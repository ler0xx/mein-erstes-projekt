#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MEPFlowerActor.generated.h"

class UStaticMesh;
class UMaterialInstanceDynamic;
class UMEPThemeSubsystem;

/**
 * Die Blume aus images/blume.svg, zusammengesetzt aus Grundformen der Engine:
 * flache Kugeln für Blütenblätter, Blätter, Wiese und Blütenmitte, Zylinder für den
 * Stiel und ein flacher Würfel als Himmel-Karte.
 *
 * Sie wächst beim Start auf (flower-grow) und schwingt danach sanft (flower-sway);
 * bei reduzierter Bewegung steht sie still – wie auf der Website.
 *
 * Wo sie steht, bestimmt das UI: Das Hero-Widget reserviert einen Platz im Layout und
 * meldet dessen Position in Viewport-Pixeln (SetScreenRect).
 */
UCLASS()
class AMEPFlowerActor : public AActor
{
	GENERATED_BODY()

public:
	AMEPFlowerActor();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

	// Mittelpunkt und Höhe des Platzes für die Blume, in Viewport-Pixeln.
	void SetScreenRect(const FVector2D& CenterPixels, float HeightPixels);

private:
	void BuildFlower();
	void AddPart(UStaticMesh* Mesh, const FString& Hex, double SvgX, double SvgY, double Depth,
		const FVector& Size, double RollRadians = 0.f);
	void AddPart(UStaticMesh* Mesh, const FString& Hex, double SvgX, double SvgY, double Depth,
		const FVector& Size, const FQuat& Rotation);
	void ApplyTheme();

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<USceneComponent> SceneRoot;

	// Drehpunkt unten in der Mitte (transform-origin: 50% 100%).
	UPROPERTY(VisibleAnywhere)
	TObjectPtr<USceneComponent> Pivot;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CubeMesh;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> SphereMesh;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CylinderMesh;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> PartMaterials;

	UPROPERTY(Transient)
	TObjectPtr<UMEPThemeSubsystem> Theme;

	TArray<FLinearColor> PartColors;
	FDelegateHandle ThemeHandle;
	bool bHasScreenRect = false;
	float AnimTime = 0.f;
	float FigureScale = 1.f;
};
