#include "MEPPlayerController.h"

#include "MEPGameMode.h"
#include "MEPHeroWidget.h"
#include "Blueprint/UserWidget.h"
#include "Camera/CameraActor.h"
#include "Engine/World.h"

AMEPPlayerController::AMEPPlayerController()
{
	// Die Kamera wird selbst gesetzt; beim Besetzen des Pawns nicht wieder umschalten.
	bAutoManageActiveCameraTarget = false;
	bShowMouseCursor = true;
	bEnableClickEvents = false;
	bEnableMouseOverEvents = false;
}

void AMEPPlayerController::BeginPlay()
{
	Super::BeginPlay();

	if (!IsLocalController())
	{
		return;
	}

	AMEPGameMode* GameMode = GetWorld()->GetAuthGameMode<AMEPGameMode>();
	if (GameMode && GameMode->GetSceneCamera())
	{
		SetViewTarget(GameMode->GetSceneCamera());
	}

	FInputModeGameAndUI InputMode;
	InputMode.SetHideCursorDuringCapture(false);
	InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	SetInputMode(InputMode);

	HeroWidget = CreateWidget<UMEPHeroWidget>(this, UMEPHeroWidget::StaticClass());
	if (HeroWidget)
	{
		if (GameMode)
		{
			HeroWidget->SetSceneActors(GameMode->GetFlowField(), GameMode->GetFlower());
		}
		HeroWidget->AddToViewport();
	}
}
