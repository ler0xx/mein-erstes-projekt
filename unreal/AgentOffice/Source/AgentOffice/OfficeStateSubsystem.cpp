#include "OfficeStateSubsystem.h"

#include "AgentOffice.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace OfficeState
{
	static const TCHAR* StatusText(const FOfficeWorker& Worker)
	{
		return Worker.bWorking ? TEXT("arbeitet") : TEXT("wartet");
	}

	static bool IsHexColor(const FString& Text)
	{
		const FString Digits = Text.StartsWith(TEXT("#")) ? Text.Mid(1) : Text;
		if (Digits.Len() != 6 && Digits.Len() != 8)
		{
			return false;
		}
		for (const TCHAR Ch : Digits)
		{
			if (!FChar::IsHexDigit(Ch))
			{
				return false;
			}
		}
		return true;
	}

	/**
	 * Liest aus EINEM Eintrag von workers.json nur die erlaubten Felder.
	 * Andere Felder (hookToken, prompt, sessionId, tracker, ...) werden nie angefasst.
	 */
	static bool ReadWorker(const FJsonObject& Obj, FOfficeWorker& Out)
	{
		if (!Obj.TryGetStringField(TEXT("id"), Out.Id) || Out.Id.IsEmpty())
		{
			return false;
		}

		Obj.TryGetStringField(TEXT("name"), Out.Name);
		Obj.TryGetStringField(TEXT("deskId"), Out.DeskId);
		Obj.TryGetStringField(TEXT("color"), Out.ColorHex);
		Obj.TryGetStringField(TEXT("activity"), Out.Activity);
		Obj.TryGetBoolField(TEXT("midTurn"), Out.bWorking);

		const TSharedPtr<FJsonObject>* TaskObj = nullptr;
		if (Obj.TryGetObjectField(TEXT("task"), TaskObj) && TaskObj && TaskObj->IsValid())
		{
			(*TaskObj)->TryGetStringField(TEXT("name"), Out.TaskName);
		}

		if (Out.Name.IsEmpty())
		{
			Out.Name = Out.Id;
		}

		if (IsHexColor(Out.ColorHex))
		{
			Out.Color = FLinearColor::FromSRGBColor(FColor::FromHex(Out.ColorHex));
		}

		return true;
	}
}

UOfficeStateSubsystem::UOfficeStateSubsystem()
{
	OfficeDir = TEXT("C:/Users/info/agent-office/ler0xx/mein-erstes-projekt/.agent-office");
}

void UOfficeStateSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);

	ResolveOfficeDir();
	UE_LOG(LogAgentOffice, Log, TEXT("Agent Office: lese Zustand aus %s (alle %.1f s)"), *GetWorkersFilePath(), PollIntervalSeconds);

	Poll(/*bForce*/ true);

	TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
		FTickerDelegate::CreateUObject(this, &UOfficeStateSubsystem::HandleTicker),
		FMath::Max(0.25f, PollIntervalSeconds));
}

void UOfficeStateSubsystem::Deinitialize()
{
	FTSTicker::RemoveTicker(TickerHandle);
	TickerHandle.Reset();
	Workers.Reset();

	Super::Deinitialize();
}

void UOfficeStateSubsystem::ResolveOfficeDir()
{
	FString Dir = OfficeDir;

	FString FromCommandLine;
	if (FParse::Value(FCommandLine::Get(), TEXT("OfficeDir="), FromCommandLine) && !FromCommandLine.IsEmpty())
	{
		Dir = FromCommandLine;
	}

	Dir.TrimStartAndEndInline();
	if (FPaths::IsRelative(Dir))
	{
		Dir = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir(), Dir);
	}
	FPaths::NormalizeDirectoryName(Dir);
	ResolvedOfficeDir = Dir;
}

FString UOfficeStateSubsystem::GetWorkersFilePath() const
{
	return FPaths::Combine(ResolvedOfficeDir, TEXT("workers.json"));
}

bool UOfficeStateSubsystem::FindWorker(const FString& WorkerId, FOfficeWorker& OutWorker) const
{
	if (const FOfficeWorker* Found = Workers.FindByPredicate([&](const FOfficeWorker& W) { return W.Id == WorkerId; }))
	{
		OutWorker = *Found;
		return true;
	}
	return false;
}

void UOfficeStateSubsystem::SetOfficeDir(const FString& NewOfficeDir)
{
	OfficeDir = NewOfficeDir;
	// Kommandozeile soll einen expliziten Laufzeit-Wechsel nicht überstimmen
	FString Dir = NewOfficeDir;
	if (FPaths::IsRelative(Dir))
	{
		Dir = FPaths::ConvertRelativePathToFull(FPaths::ProjectDir(), Dir);
	}
	FPaths::NormalizeDirectoryName(Dir);
	ResolvedOfficeDir = Dir;

	LastModified = FDateTime::MinValue();
	LastFileSize = -1;
	bWarnedMissing = false;
	bWarnedInvalid = false;
	UE_LOG(LogAgentOffice, Log, TEXT("Agent Office: neuer Ordner %s"), *ResolvedOfficeDir);
	Poll(/*bForce*/ true);
}

void UOfficeStateSubsystem::RefreshNow()
{
	Poll(/*bForce*/ true);
}

bool UOfficeStateSubsystem::HandleTicker(float DeltaTime)
{
	Poll(/*bForce*/ false);
	return true; // weiter ticken
}

void UOfficeStateSubsystem::Poll(bool bForce)
{
	const FString Path = GetWorkersFilePath();
	const FFileStatData Stat = IFileManager::Get().GetStatData(*Path);

	if (!Stat.bIsValid || Stat.bIsDirectory)
	{
		bSourceHealthy = false;
		LastModified = FDateTime::MinValue();
		LastFileSize = -1;
		++MissingPolls;

		if (!bWarnedMissing)
		{
			UE_LOG(LogAgentOffice, Warning, TEXT("Agent Office: %s nicht gefunden – warte darauf. Ordner einstellbar mit -OfficeDir=\"...\""), *Path);
			bWarnedMissing = true;
		}

		// Kurzes Fehlen (z. B. während die Datei ersetzt wird) ignorieren, längeres = Büro leer
		if (MissingPolls >= FMath::Max(1, MissingFileGracePolls) && Workers.Num() > 0)
		{
			ApplyWorkers(TArray<FOfficeWorker>());
		}
		return;
	}

	MissingPolls = 0;
	if (bWarnedMissing)
	{
		UE_LOG(LogAgentOffice, Log, TEXT("Agent Office: workers.json gefunden."));
		bWarnedMissing = false;
	}

	if (!bForce && Stat.ModificationTime == LastModified && Stat.FileSize == LastFileSize)
	{
		return; // unverändert
	}

	TArray<uint8> Bytes;
	// AllowWrite: das Agent Office darf die Datei weiter schreiben, während wir lesen
	if (!FFileHelper::LoadFileToArray(Bytes, *Path, FILEREAD_AllowWrite | FILEREAD_Silent))
	{
		return; // gesperrt o. Ä. – nächster Takt versucht es erneut
	}

	int32 Offset = 0;
	if (Bytes.Num() >= 3 && Bytes[0] == 0xEF && Bytes[1] == 0xBB && Bytes[2] == 0xBF)
	{
		Offset = 3; // UTF-8-BOM überspringen
	}

	TArray<FOfficeWorker> Parsed;
	bool bParsed = false;
	{
		const FUTF8ToTCHAR Converted(reinterpret_cast<const ANSICHAR*>(Bytes.GetData() + Offset), Bytes.Num() - Offset);
		const FString JsonText(Converted.Length(), Converted.Get());
		bParsed = ParseWorkersJson(JsonText, Parsed);
	}
	// Rohdaten sofort verwerfen – darin stehen auch Felder, die uns nichts angehen
	Bytes.Empty();

	if (!bParsed)
	{
		bSourceHealthy = false;
		if (!bWarnedInvalid)
		{
			// Bewusst ohne Dateiinhalt/Fehlertext loggen
			UE_LOG(LogAgentOffice, Warning, TEXT("Agent Office: workers.json ist gerade nicht lesbar (ungültiges JSON, evtl. halb geschrieben) – behalte letzten Stand."));
			bWarnedInvalid = true;
		}
		return;
	}

	bWarnedInvalid = false;
	bSourceHealthy = true;
	LastModified = Stat.ModificationTime;
	LastFileSize = Stat.FileSize;

	ApplyWorkers(MoveTemp(Parsed));
}

bool UOfficeStateSubsystem::ParseWorkersJson(const FString& JsonText, TArray<FOfficeWorker>& OutWorkers)
{
	OutWorkers.Reset();

	TSharedPtr<FJsonValue> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return false;
	}

	// Erwartet wird eine Liste; zur Sicherheit auch {"workers": [...]} akzeptieren
	const TArray<TSharedPtr<FJsonValue>>* Entries = nullptr;
	if (!Root->TryGetArray(Entries))
	{
		const TSharedPtr<FJsonObject>* RootObj = nullptr;
		if (!Root->TryGetObject(RootObj) || !RootObj || !(*RootObj)->TryGetArrayField(TEXT("workers"), Entries))
		{
			return false;
		}
	}

	for (const TSharedPtr<FJsonValue>& Entry : *Entries)
	{
		const TSharedPtr<FJsonObject>* Obj = nullptr;
		if (!Entry.IsValid() || !Entry->TryGetObject(Obj) || !Obj || !Obj->IsValid())
		{
			continue;
		}

		FOfficeWorker Worker;
		if (OfficeState::ReadWorker(**Obj, Worker))
		{
			OutWorkers.Add(MoveTemp(Worker));
		}
	}
	return true;
}

void UOfficeStateSubsystem::ApplyWorkers(TArray<FOfficeWorker>&& NewWorkers)
{
	TMap<FString, int32> OldIndexById;
	for (int32 Index = 0; Index < Workers.Num(); ++Index)
	{
		OldIndexById.Add(Workers[Index].Id, Index);
	}

	TSet<FString> NewIds;
	TArray<FOfficeWorker> Unique;
	TArray<FOfficeWorker> Arrived;
	TArray<TPair<FOfficeWorker, FOfficeWorker>> Changed; // (neu, alt)

	for (FOfficeWorker& Worker : NewWorkers)
	{
		bool bAlreadyThere = false;
		NewIds.Add(Worker.Id, &bAlreadyThere);
		if (bAlreadyThere)
		{
			continue; // doppelte id – erster Eintrag gewinnt
		}

		if (const int32* OldIndex = OldIndexById.Find(Worker.Id))
		{
			if (!Workers[*OldIndex].HasSameState(Worker))
			{
				Changed.Emplace(Worker, Workers[*OldIndex]);
			}
		}
		else
		{
			Arrived.Add(Worker);
		}
		Unique.Add(MoveTemp(Worker));
	}

	TArray<FOfficeWorker> Left;
	for (const FOfficeWorker& Old : Workers)
	{
		if (!NewIds.Contains(Old.Id))
		{
			Left.Add(Old);
		}
	}

	if (Arrived.IsEmpty() && Left.IsEmpty() && Changed.IsEmpty())
	{
		return;
	}

	// Zuerst den Zustand übernehmen, damit Event-Empfänger einen konsistenten Stand sehen
	Workers = MoveTemp(Unique);

	for (const FOfficeWorker& Worker : Left)
	{
		UE_LOG(LogAgentOffice, Log, TEXT("Mitarbeiter gegangen: %s (%s)"), *Worker.Name, *Worker.DeskId);
		OnWorkerLeft.Broadcast(Worker);
	}

	for (const TPair<FOfficeWorker, FOfficeWorker>& Pair : Changed)
	{
		const FOfficeWorker& Now = Pair.Key;
		const FOfficeWorker& Before = Pair.Value;
		if (Now.bWorking != Before.bWorking || Now.DeskId != Before.DeskId)
		{
			UE_LOG(LogAgentOffice, Log, TEXT("Mitarbeiter %s: %s, Platz %s"), *Now.Name, OfficeState::StatusText(Now), *Now.DeskId);
		}
		else
		{
			UE_LOG(LogAgentOffice, Verbose, TEXT("Mitarbeiter %s: Details geändert"), *Now.Name);
		}
		OnWorkerChanged.Broadcast(Now, Before);
	}

	for (const FOfficeWorker& Worker : Arrived)
	{
		UE_LOG(LogAgentOffice, Log, TEXT("Mitarbeiter da: %s (%s, %s)"), *Worker.Name, *Worker.DeskId, OfficeState::StatusText(Worker));
		OnWorkerArrived.Broadcast(Worker);
	}

	OnWorkersUpdated.Broadcast();
}
