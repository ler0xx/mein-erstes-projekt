#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "OfficeTypes.h"
#include "OfficeDirector.generated.h"

class AAgentCharacter;
class UOfficeStateSubsystem;
class USkeletalMesh;

/**
 * Regie im Level: lädt den Grundriss und setzt für jeden Mitarbeiter aus
 * workers.json eine Figur (AAgentCharacter) an ihren Platz. Kommt jemand,
 * geht jemand oder ändert sich sein Status, wird die Figur angepasst.
 *
 * Die Koordinaten im Grundriss sind relativ zu diesem Actor (im Testlevel
 * steht er in der Raummitte). Bedeutung von x/y je Platztyp: siehe FOfficeDeskSpot.
 */
UCLASS(Config = Game)
class AGENTOFFICE_API AOfficeDirector : public AActor
{
	GENERATED_BODY()

public:
	AOfficeDirector();

	/** Grundriss neu laden und alle Figuren neu platzieren. */
	UFUNCTION(BlueprintCallable, Category = "Agent Office")
	void ReloadLayout();

	UFUNCTION(BlueprintPure, Category = "Agent Office")
	AAgentCharacter* FindAgent(const FString& WorkerId) const;

	UFUNCTION(BlueprintPure, Category = "Agent Office")
	TArray<FOfficeDeskSpot> GetDeskSpots() const { return Spots; }

	/** Welttransform eines Platzes, so wie er in DeskLayout.json steht (z. B. Tischmitte). */
	UFUNCTION(BlueprintPure, Category = "Agent Office")
	bool GetSpotWorldTransform(const FString& DeskId, FTransform& OutTransform) const;

	/** Wo die Person an diesem Platz steht/sitzt (Welt), mit ihrer Blickrichtung. */
	UFUNCTION(BlueprintPure, Category = "Agent Office")
	bool GetPersonWorldTransform(const FString& DeskId, FTransform& OutTransform) const;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	/** Grundriss-Datei. Relativ = relativ zum Content-Ordner. */
	UPROPERTY(EditAnywhere, Config, Category = "Agent Office|Grundriss")
	FString LayoutFile = TEXT("Data/DeskLayout.json");

	/** Abstand Tischmitte -> Person bei "desk" (cm, entgegen der Blickrichtung). */
	UPROPERTY(EditAnywhere, Config, Category = "Agent Office|Grundriss")
	float DeskSeatOffset = 75.f;

	/** Abstand Tafel -> Person bei "station" (cm, entgegen der Blickrichtung). */
	UPROPERTY(EditAnywhere, Config, Category = "Agent Office|Grundriss")
	float StationStandOffset = 70.f;

	/** Platz für Mitarbeiter, deren deskId nicht im Grundriss steht (relativ zu diesem Actor; Lounge im Südwesten). */
	UPROPERTY(EditAnywhere, Category = "Agent Office|Grundriss")
	FVector LobbyLocation = FVector(-680.f, 400.f, 0.f);

	/** Blickrichtung der Wartenden in der Lobby (-90 = Richtung Norden/Tische). */
	UPROPERTY(EditAnywhere, Category = "Agent Office|Grundriss")
	float LobbyYaw = -90.f;

	/** Abstand zwischen Wartenden in der Lobby (cm, nebeneinander). */
	UPROPERTY(EditAnywhere, Category = "Agent Office|Grundriss")
	float LobbySpacing = 90.f;

	/** Seitlicher Abstand, wenn sich mehrere Mitarbeiter einen Platz teilen (cm). */
	UPROPERTY(EditAnywhere, Category = "Agent Office|Grundriss")
	float SharedSpotSpacing = 80.f;

	/** Figur-Klasse. Für MetaHumans eine Blueprint-Unterklasse von AgentCharacter eintragen. */
	UPROPERTY(EditAnywhere, Config, NoClear, Category = "Agent Office|Agenten")
	TSubclassOf<AAgentCharacter> AgentClass;

	/** Optional: nur das Skeletal Mesh aller Figuren austauschen. */
	UPROPERTY(EditAnywhere, Config, Category = "Agent Office|Agenten")
	TSoftObjectPtr<USkeletalMesh> AgentMeshOverride;

	/** Aktuell gespawnte Figuren, nach Mitarbeiter-id. */
	UPROPERTY(VisibleInstanceOnly, Transient, Category = "Agent Office|Agenten")
	TMap<FString, TObjectPtr<AAgentCharacter>> Agents;

private:
	UFUNCTION()
	void HandleWorkerArrived(const FOfficeWorker& Worker);

	UFUNCTION()
	void HandleWorkerLeft(const FOfficeWorker& Worker);

	UFUNCTION()
	void HandleWorkerChanged(const FOfficeWorker& Worker, const FOfficeWorker& Previous);

	void SpawnAgent(const FOfficeWorker& Worker);
	void PlaceAgent(AAgentCharacter* Agent, const FOfficeWorker& Worker);
	FTransform PersonLocalTransform(const FOfficeDeskSpot& Spot) const;
	FTransform ComputeAgentTransform(const FOfficeWorker& Worker, const AAgentCharacter* Self, FString& OutSpotType) const;

	TArray<FOfficeDeskSpot> Spots;
	TMap<FString, int32> SpotIndexById;
	TWeakObjectPtr<UOfficeStateSubsystem> StateSubsystem;
	mutable TSet<FString> WarnedUnknownDesks;
};
