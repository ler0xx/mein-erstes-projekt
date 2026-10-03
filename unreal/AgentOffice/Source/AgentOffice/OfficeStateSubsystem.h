#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "OfficeTypes.h"
#include "OfficeStateSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOfficeWorkerEvent, const FOfficeWorker&, Worker);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FOfficeWorkerChangedEvent, const FOfficeWorker&, Worker, const FOfficeWorker&, Previous);
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOfficeWorkersUpdatedEvent);

/**
 * Liest den Live-Zustand des Agent Office.
 *
 * Alle PollIntervalSeconds (Standard: 2 s) wird <OfficeDir>/workers.json gelesen.
 * Übernommen werden nur id, name, deskId, color, activity, midTurn und task.name.
 * Fehlt die Datei oder ist sie kaputt, bleibt der letzte gültige Zustand erhalten
 * (fehlt sie mehrere Male hintereinander, gilt das Büro als leer).
 *
 * Ordner einstellen:
 *   - DefaultGame.ini:  [/Script/AgentOffice.OfficeStateSubsystem] OfficeDir=...
 *   - Kommandozeile:    -OfficeDir="C:/pfad/zu/.agent-office"   (hat Vorrang)
 */
UCLASS(Config = Game)
class AGENTOFFICE_API UOfficeStateSubsystem : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	UOfficeStateSubsystem();

	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** Alle Mitarbeiter, die gerade im Büro sind. */
	UFUNCTION(BlueprintPure, Category = "Agent Office")
	TArray<FOfficeWorker> GetWorkers() const { return Workers; }

	const TArray<FOfficeWorker>& GetWorkersRef() const { return Workers; }

	UFUNCTION(BlueprintPure, Category = "Agent Office")
	bool FindWorker(const FString& WorkerId, FOfficeWorker& OutWorker) const;

	/** Der tatsächlich benutzte Office-Ordner (nach Config + Kommandozeile). */
	UFUNCTION(BlueprintPure, Category = "Agent Office")
	FString GetOfficeDir() const { return ResolvedOfficeDir; }

	UFUNCTION(BlueprintPure, Category = "Agent Office")
	FString GetWorkersFilePath() const;

	/** true, wenn workers.json beim letzten Lesen gefunden und gültig war. */
	UFUNCTION(BlueprintPure, Category = "Agent Office")
	bool IsSourceHealthy() const { return bSourceHealthy; }

	/** Office-Ordner zur Laufzeit wechseln; liest sofort neu ein. */
	UFUNCTION(BlueprintCallable, Category = "Agent Office")
	void SetOfficeDir(const FString& NewOfficeDir);

	/** Sofort neu einlesen, ohne auf den nächsten Takt zu warten. */
	UFUNCTION(BlueprintCallable, Category = "Agent Office")
	void RefreshNow();

	/** Ein Mitarbeiter ist neu im Büro. */
	UPROPERTY(BlueprintAssignable, Category = "Agent Office")
	FOfficeWorkerEvent OnWorkerArrived;

	/** Ein Mitarbeiter hat das Büro verlassen. */
	UPROPERTY(BlueprintAssignable, Category = "Agent Office")
	FOfficeWorkerEvent OnWorkerLeft;

	/** Status, Platz, Aufgabe o. Ä. eines Mitarbeiters hat sich geändert. */
	UPROPERTY(BlueprintAssignable, Category = "Agent Office")
	FOfficeWorkerChangedEvent OnWorkerChanged;

	/** Wird nach jeder Änderung (nach den Einzel-Events) einmal ausgelöst. */
	UPROPERTY(BlueprintAssignable, Category = "Agent Office")
	FOfficeWorkersUpdatedEvent OnWorkersUpdated;

	/**
	 * Wandelt den Inhalt von workers.json in Mitarbeiter um. Liest nur die
	 * erlaubten Felder; gibt false zurück, wenn das JSON ungültig ist.
	 */
	static bool ParseWorkersJson(const FString& JsonText, TArray<FOfficeWorker>& OutWorkers);

protected:
	/** Ordner des Agent Office (enthält workers.json). */
	UPROPERTY(Config)
	FString OfficeDir;

	/** Wie oft workers.json gelesen wird (Sekunden). */
	UPROPERTY(Config)
	float PollIntervalSeconds = 2.f;

	/** So oft hintereinander darf die Datei fehlen, bevor das Büro als leer gilt. */
	UPROPERTY(Config)
	int32 MissingFileGracePolls = 3;

private:
	bool HandleTicker(float DeltaTime);
	void Poll(bool bForce);
	void ApplyWorkers(TArray<FOfficeWorker>&& NewWorkers);
	void ResolveOfficeDir();

	TArray<FOfficeWorker> Workers;
	FString ResolvedOfficeDir;
	FTSTicker::FDelegateHandle TickerHandle;

	FDateTime LastModified = FDateTime::MinValue();
	int64 LastFileSize = -1;
	int32 MissingPolls = 0;
	bool bSourceHealthy = false;
	bool bWarnedMissing = false;
	bool bWarnedInvalid = false;
};
