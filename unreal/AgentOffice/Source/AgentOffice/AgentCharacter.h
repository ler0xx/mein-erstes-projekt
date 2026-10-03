#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "OfficeTypes.h"
#include "AgentCharacter.generated.h"

class SImage;
class STextBlock;
class UAnimationAsset;
class URectLightComponent;
class USceneComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class UWidgetComponent;

/**
 * Ein Agent als Person im Büro.
 *
 * Steht im Ursprung des Actors und schaut entlang +X (Richtung Tisch).
 * Aussehen austauschbar:
 *   - Blueprint-Unterklasse anlegen und BodyMesh/Animationen setzen
 *     (später: MetaHuman im dunklen Anzug mit Sonnenbrille), oder
 *   - in DefaultGame.ini AgentMeshOverride am AOfficeDirector setzen.
 *
 * "Arbeitet" vs. "wartet":
 *   - Bildschirm-Licht am Tisch an/aus (kühles Monitorlicht im Gesicht),
 *   - Animation läuft normal bzw. ruhiger,
 *   - Statuszeile im Namensschild.
 */
UCLASS(Blueprintable)
class AGENTOFFICE_API AAgentCharacter : public AActor
{
	GENERATED_BODY()

public:
	AAgentCharacter();

	/** Daten aus workers.json übernehmen (Name, Aufgabe, Status, Farbe). */
	UFUNCTION(BlueprintCallable, Category = "Agent")
	void ApplyWorker(const FOfficeWorker& InWorker);

	/** Art des Platzes aus dem Grundriss ("desk", "station", "meeting"). */
	UFUNCTION(BlueprintCallable, Category = "Agent")
	void SetSpotType(const FString& InSpotType);

	/** Skeletal Mesh zur Laufzeit tauschen. */
	UFUNCTION(BlueprintCallable, Category = "Agent")
	void SetBodyMesh(USkeletalMesh* NewMesh);

	UFUNCTION(BlueprintPure, Category = "Agent")
	const FOfficeWorker& GetWorker() const { return Worker; }

	UFUNCTION(BlueprintPure, Category = "Agent")
	bool IsWorking() const { return Worker.bWorking; }

	/** Für Blueprints (z. B. MetaHuman-Animationen): wird nach jeder Änderung aufgerufen. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Agent")
	void OnWorkerUpdated(const FOfficeWorker& UpdatedWorker, bool bWorkingChanged);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Agent")
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Agent")
	TObjectPtr<USkeletalMeshComponent> Body;

	/** Bildschirmlicht am Tisch – leuchtet, wenn der Agent arbeitet. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Agent")
	TObjectPtr<URectLightComponent> ScreenLight;

	/** Namensschild über dem Kopf (Bildschirm-Overlay, unabhängig von der Belichtung lesbar). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Agent")
	TObjectPtr<UWidgetComponent> NamePlate;

	/** Figur. Platzhalter: Engine-Mannequin. Später: MetaHuman. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Aussehen")
	TSoftObjectPtr<USkeletalMesh> BodyMesh;

	/** Drehung des Meshes, damit es entlang +X schaut (UE-Mannequins schauen entlang +Y). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Aussehen")
	float BodyMeshYaw = -90.f;

	/** Platzhalter-Mesh dunkel einfärben (angedeuteter dunkler Anzug). Für MetaHumans ausschalten. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Aussehen")
	bool bTintPlaceholder = true;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Aussehen", meta = (EditCondition = "bTintPlaceholder"))
	FLinearColor PlaceholderSuitColor = FLinearColor(0.012f, 0.012f, 0.014f, 1.f);

	/** Animation während der Arbeit. Leer lassen, wenn ein Anim-Blueprint die Figur steuert. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Animation")
	TSoftObjectPtr<UAnimationAsset> WorkingAnimation;

	/** Animation beim Warten. Leer = WorkingAnimation. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Animation")
	TSoftObjectPtr<UAnimationAsset> WaitingAnimation;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Animation")
	float WorkingPlayRate = 1.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Animation")
	float WaitingPlayRate = 0.55f;

	/** Bildschirmlicht in Lumen (ein Monitor liegt grob bei 100–200 lm). */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Licht")
	float ScreenLightWorkingLumens = 160.f;

	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Agent|Licht")
	float ScreenLightWaitingLumens = 8.f;

private:
	void ApplyBodyMesh(USkeletalMesh* Mesh, bool bIsPlaceholder);
	void UpdateAnimation(bool bRestart);
	void UpdateScreenLight();
	void BuildNamePlate();
	void UpdateNamePlate();

	FOfficeWorker Worker;
	FString SpotType = TEXT("desk");
	bool bHasWorker = false;
	TWeakObjectPtr<UAnimationAsset> PlayingAnimation;

	TSharedPtr<STextBlock> NameText;
	TSharedPtr<STextBlock> TaskText;
	TSharedPtr<STextBlock> StatusText;
	TSharedPtr<SImage> AccentBar;
	TSharedPtr<SImage> StatusDot;
};
