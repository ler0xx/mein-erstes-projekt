#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "OfficeTypes.h"
#include "OfficeLayout.generated.h"

/**
 * Lädt den Grundriss (DeskLayout.json):
 * [{"deskId":"desk-1","label":"Schreibtisch 1","type":"desk","x":0,"y":0,"yaw":0}, ...]
 */
UCLASS()
class AGENTOFFICE_API UOfficeLayoutLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Relativer Pfad = relativ zum Content-Ordner des Projekts. */
	UFUNCTION(BlueprintPure, Category = "Agent Office|Layout")
	static FString ResolveLayoutPath(const FString& LayoutFile);

	/** Liest die Datei; false, wenn sie fehlt oder kein gültiges JSON ist. */
	UFUNCTION(BlueprintCallable, Category = "Agent Office|Layout")
	static bool LoadDeskLayout(const FString& LayoutFile, TArray<FOfficeDeskSpot>& OutSpots);

	static bool ParseDeskLayoutJson(const FString& JsonText, TArray<FOfficeDeskSpot>& OutSpots);
};
