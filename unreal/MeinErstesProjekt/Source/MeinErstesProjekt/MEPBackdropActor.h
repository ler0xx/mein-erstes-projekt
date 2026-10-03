#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MEPBackdropActor.generated.h"

class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UMEPThemeSubsystem;

/**
 * Der Seitenhintergrund aus style.css: eine Fläche in --bg und darüber ein
 * elliptischer Verlauf zu --bg-glow (radial-gradient(ellipse at 50% 40%, …)).
 * Der Verlauf wird aus gestapelten, flachen Zylinderscheiben angenähert.
 */
UCLASS()
class AMEPBackdropActor : public AActor
{
	GENERATED_BODY()

public:
	AMEPBackdropActor();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
	virtual void Tick(float DeltaSeconds) override;

private:
	void ApplyTheme();
	void UpdateLayout();

	UPROPERTY(VisibleAnywhere)
	TObjectPtr<USceneComponent> SceneRoot;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CubeMesh;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> CylinderMesh;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMeshComponent> Base;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Rings;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInstanceDynamic>> Materials;

	UPROPERTY(Transient)
	TObjectPtr<UMEPThemeSubsystem> Theme;

	float LastHeight = -1.f;
	FDelegateHandle ThemeHandle;
};
