#pragma once

#include "CoreMinimal.h"
#include "OfficeTypes.generated.h"

/**
 * Ein Mitarbeiter (KI-Agent) aus workers.json.
 *
 * Enthält bewusst NUR unkritische Felder. Alles andere aus der Datei
 * (z. B. hookToken, prompt, sessionId, tracker) wird beim Einlesen
 * übersprungen und nirgends gespeichert.
 */
USTRUCT(BlueprintType)
struct AGENTOFFICE_API FOfficeWorker
{
	GENERATED_BODY()

	/** Eindeutige Kennung ("id"). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Office")
	FString Id;

	/** Anzeigename ("name"). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Office")
	FString Name;

	/** Platz im Grundriss ("deskId"), z. B. "desk-3" oder "meeting-1". */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Office")
	FString DeskId;

	/** Agentenfarbe wie in der Datei ("color", z. B. "#118ab2"). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Office")
	FString ColorHex;

	/** Agentenfarbe als Farbwert (grau, wenn "color" fehlt oder ungültig ist). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Office")
	FLinearColor Color = FLinearColor(0.5f, 0.5f, 0.5f, 1.f);

	/** Letzte Tätigkeit ("activity"). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Office")
	FString Activity;

	/** true = arbeitet gerade ("midTurn"), false = wartet. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Office")
	bool bWorking = false;

	/** Name der aktuellen Aufgabe ("task.name"). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Office")
	FString TaskName;

	bool HasSameState(const FOfficeWorker& Other) const
	{
		return Id == Other.Id
			&& Name == Other.Name
			&& DeskId == Other.DeskId
			&& ColorHex == Other.ColorHex
			&& Activity == Other.Activity
			&& bWorking == Other.bWorking
			&& TaskName == Other.TaskName;
	}
};

/**
 * Ein Platz im Grundriss (ein Eintrag aus DeskLayout.json).
 *
 * Konvention wie im Designkonzept (docs/agent-office-ue5/konzept.md):
 * Einheit cm, Ursprung = Raummitte auf Bodenhöhe (bzw. der AOfficeDirector),
 * Yaw = Blickrichtung der Person in Grad (0 = +X, 90 = +Y, 180 = -X, 270 = -Y).
 * X/Y bedeuten je nach Typ:
 *   - "desk":    Mitte der Tischplatte; die Person sitzt 75 cm entgegen der Blickrichtung
 *   - "station": Mitte der Wandtafel; die Person steht ca. 70 cm davor
 *   - "meeting": Mitte des Stuhls (= Platz der Person)
 */
USTRUCT(BlueprintType)
struct AGENTOFFICE_API FOfficeDeskSpot
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Office")
	FString DeskId;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Office")
	FString Label;

	/** "desk", "station" oder "meeting". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Office")
	FString Type = TEXT("desk");

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Office")
	float X = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Office")
	float Y = 0.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Office")
	float Yaw = 0.f;

	FTransform ToLocalTransform() const
	{
		return FTransform(FRotator(0.f, Yaw, 0.f), FVector(X, Y, 0.f));
	}
};
