#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "MEPGameMode.generated.h"

class ACameraActor;
class AMEPBackdropActor;
class AMEPFlowFieldActor;
class AMEPFlowerActor;

/**
 * Baut die ganze Szene zur Laufzeit auf, damit das Projekt ohne eigene Assets
 * auskommt: orthografische Kamera, Hintergrund, Strömungsfeld und Blume.
 * Die Map selbst ist die leere Entry-Map der Engine.
 */
UCLASS()
class AMEPGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AMEPGameMode();

	virtual void StartPlay() override;

	ACameraActor* GetSceneCamera() const { return SceneCamera; }
	AMEPFlowFieldActor* GetFlowField() const { return FlowField; }
	AMEPFlowerActor* GetFlower() const { return Flower; }

private:
	void SpawnScene();

	UPROPERTY(Transient)
	TObjectPtr<ACameraActor> SceneCamera;

	UPROPERTY(Transient)
	TObjectPtr<AMEPBackdropActor> Backdrop;

	UPROPERTY(Transient)
	TObjectPtr<AMEPFlowFieldActor> FlowField;

	UPROPERTY(Transient)
	TObjectPtr<AMEPFlowerActor> Flower;
};
