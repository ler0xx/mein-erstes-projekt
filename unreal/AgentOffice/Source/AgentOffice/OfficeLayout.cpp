#include "OfficeLayout.h"

#include "AgentOffice.h"
#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

FString UOfficeLayoutLibrary::ResolveLayoutPath(const FString& LayoutFile)
{
	if (FPaths::IsRelative(LayoutFile))
	{
		return FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir(), LayoutFile);
	}
	return LayoutFile;
}

bool UOfficeLayoutLibrary::LoadDeskLayout(const FString& LayoutFile, TArray<FOfficeDeskSpot>& OutSpots)
{
	OutSpots.Reset();
	const FString Path = ResolveLayoutPath(LayoutFile);

	FString JsonText;
	if (!FFileHelper::LoadFileToString(JsonText, *Path))
	{
		UE_LOG(LogAgentOffice, Warning, TEXT("Grundriss nicht gefunden: %s"), *Path);
		return false;
	}

	if (!ParseDeskLayoutJson(JsonText, OutSpots))
	{
		UE_LOG(LogAgentOffice, Warning, TEXT("Grundriss ist kein gültiges JSON (erwartet: Liste von Plätzen): %s"), *Path);
		return false;
	}

	UE_LOG(LogAgentOffice, Log, TEXT("Grundriss geladen: %d Plätze aus %s"), OutSpots.Num(), *Path);
	return true;
}

bool UOfficeLayoutLibrary::ParseDeskLayoutJson(const FString& JsonText, TArray<FOfficeDeskSpot>& OutSpots)
{
	TArray<TSharedPtr<FJsonValue>> Entries;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
	if (!FJsonSerializer::Deserialize(Reader, Entries))
	{
		return false;
	}

	for (const TSharedPtr<FJsonValue>& Entry : Entries)
	{
		const TSharedPtr<FJsonObject>* Obj = nullptr;
		if (!Entry.IsValid() || !Entry->TryGetObject(Obj) || !Obj || !Obj->IsValid())
		{
			continue;
		}

		FOfficeDeskSpot Spot;
		if (!(*Obj)->TryGetStringField(TEXT("deskId"), Spot.DeskId) || Spot.DeskId.IsEmpty())
		{
			continue;
		}
		(*Obj)->TryGetStringField(TEXT("label"), Spot.Label);
		(*Obj)->TryGetStringField(TEXT("type"), Spot.Type);

		double Number = 0.0;
		if ((*Obj)->TryGetNumberField(TEXT("x"), Number)) { Spot.X = static_cast<float>(Number); }
		if ((*Obj)->TryGetNumberField(TEXT("y"), Number)) { Spot.Y = static_cast<float>(Number); }
		if ((*Obj)->TryGetNumberField(TEXT("yaw"), Number)) { Spot.Yaw = static_cast<float>(Number); }

		OutSpots.Add(MoveTemp(Spot));
	}
	return true;
}
