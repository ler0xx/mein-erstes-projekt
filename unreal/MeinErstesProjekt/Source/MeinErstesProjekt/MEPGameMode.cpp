#include "MEPGameMode.h"

#include "MEPBackdropActor.h"
#include "MEPFlowerActor.h"
#include "MEPFlowFieldActor.h"
#include "MEPPlayerController.h"
#include "MEPThemeSubsystem.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/LightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

AMEPGameMode::AMEPGameMode()
{
	PlayerControllerClass = AMEPPlayerController::StaticClass();
	// Ein leerer Pawn: keine Steuerung, keine Kollision, nichts zu sehen.
	DefaultPawnClass = APawn::StaticClass();
}

void AMEPGameMode::StartPlay()
{
	// Vor Super::StartPlay(), damit beim BeginPlay des PlayerControllers schon alles steht.
	SpawnScene();
	Super::StartPlay();
}

void AMEPGameMode::SpawnScene()
{
	UWorld* World = GetWorld();
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;

	// Blick entlang +X auf die Bildebene: Welt-Y ist rechts, Welt-Z ist oben.
	SceneCamera = World->SpawnActor<ACameraActor>(FVector(-3000.f, 0.f, 0.f), FRotator::ZeroRotator, Params);
	if (UCameraComponent* Camera = SceneCamera->GetCameraComponent())
	{
		Camera->SetProjectionMode(ECameraProjectionMode::Orthographic);
		Camera->SetOrthoWidth(MEP::SceneWidth);
		Camera->SetOrthoNearClipPlane(1.f);
		Camera->SetOrthoFarClipPlane(10000.f);
		Camera->SetConstraintAspectRatio(false);

		// Farben sollen so aussehen wie in CSS: keine automatische Belichtung,
		// kein Bloom, keine Vignette, keine Bewegungsunschärfe.
		FPostProcessSettings& PP = Camera->PostProcessSettings;
		PP.bOverride_AutoExposureMethod = true;
		PP.AutoExposureMethod = AEM_Manual;
		PP.bOverride_AutoExposureBias = true;
		PP.AutoExposureBias = 0.f;
		PP.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
		PP.AutoExposureApplyPhysicalCameraExposure = false;
		PP.bOverride_BloomIntensity = true;
		PP.BloomIntensity = 0.f;
		PP.bOverride_VignetteIntensity = true;
		PP.VignetteIntensity = 0.f;
		PP.bOverride_MotionBlurAmount = true;
		PP.MotionBlurAmount = 0.f;
		Camera->PostProcessBlendWeight = 1.f;
	}

	// Nur nötig, wenn das unbeleuchtete Laufzeit-Material nicht gebaut werden konnte
	// (gepacktes Spiel ohne Editor-Daten): dann leuchtet ein Licht frontal auf die Szene.
	UMEPThemeSubsystem* Theme = World->GetSubsystem<UMEPThemeSubsystem>();
	if (Theme && !Theme->HasUnlitMaterial())
	{
		if (ADirectionalLight* Light = World->SpawnActor<ADirectionalLight>(FVector::ZeroVector, FRotator::ZeroRotator, Params))
		{
			Light->GetLightComponent()->SetMobility(EComponentMobility::Movable);
			Light->GetLightComponent()->SetIntensity(3.f);
		}
	}

	// Von hinten nach vorne: Hintergrund, Partikel, Blume.
	Backdrop = World->SpawnActor<AMEPBackdropActor>(FVector(300.f, 0.f, 0.f), FRotator::ZeroRotator, Params);
	FlowField = World->SpawnActor<AMEPFlowFieldActor>(FVector::ZeroVector, FRotator::ZeroRotator, Params);
	Flower = World->SpawnActor<AMEPFlowerActor>(FVector(-200.f, 0.f, 0.f), FRotator::ZeroRotator, Params);
}
