#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MEPFlowFieldActor.generated.h"

class UInstancedStaticMeshComponent;
class UMaterialInstanceDynamic;
class UMEPThemeSubsystem;

/**
 * Nachbau des Canvas-Hintergrunds aus main.js: Partikel folgen einem zeitlich
 * veränderlichen Perlin-Noise-Vektorfeld und weichen dem Mauszeiger aus.
 *
 * Jeder Partikel ist eine Instanz eines flachen Würfels, der in Bewegungsrichtung
 * gestreckt wird und so wie ein kurzer Leuchtstrich aussieht. Pro Akzentfarbe gibt
 * es eine Instanced-Static-Mesh-Komponente.
 *
 * Die Simulation rechnet wie die Website in „Bildschirm-Koordinaten“ (x nach rechts,
 * y nach unten, Ursprung oben links); erst beim Zeichnen wird auf die Bildebene
 * (Welt-Y nach rechts, Welt-Z nach oben) umgerechnet.
 */
UCLASS()
class AMEPFlowFieldActor : public AActor
{
	GENERATED_BODY()

public:
	AMEPFlowFieldActor();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

	// Läuft die Animation gerade? Berücksichtigt die Systemeinstellung „reduzierte Bewegung“,
	// solange niemand den Button gedrückt hat.
	bool IsAnimating() const;

	// Wie der Button auf der Website: merkt sich die explizite Wahl („pause“/„play“).
	void TogglePaused();

private:
	struct FParticle
	{
		float X = 0.f;
		float Y = 0.f;
		float VX = 0.f;
		float VY = 0.f;
		float Life = 0.f;
		float Size = 1.f;
		int32 Group = 0;
	};

	enum class EUserChoice : uint8
	{
		None,
		Play,
		Pause
	};

	void Spawn(FParticle& P) const;
	float FieldAngle(float X, float Y, float T) const;
	void EnsureParticleCount();
	void Step(float Dt);
	void UpdateInstances(bool bMoving);
	void ApplyTheme();
	bool GetPointer(FVector2D& OutPointer) const;

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(VisibleAnywhere)
	TArray<TObjectPtr<UInstancedStaticMeshComponent>> Layers;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> LayerMaterials;

	UPROPERTY(Transient)
	TObjectPtr<UMEPThemeSubsystem> Theme;

	TArray<FParticle> Particles;
	TArray<TArray<FTransform>> LayerTransforms;

	float Width = 1920.f;
	float Height = 1080.f;
	float Time = 0.f;
	EUserChoice UserChoice = EUserChoice::None;
	FDelegateHandle ThemeHandle;
};
