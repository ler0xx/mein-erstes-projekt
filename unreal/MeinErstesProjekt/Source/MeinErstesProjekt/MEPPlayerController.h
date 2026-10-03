#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "MEPPlayerController.generated.h"

class UMEPHeroWidget;

/**
 * Zeigt den Mauszeiger (die Partikel weichen ihm aus), schaltet auf die Szenenkamera
 * und legt das Hero-Widget in den Viewport.
 */
UCLASS()
class AMEPPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AMEPPlayerController();

	virtual void BeginPlay() override;

private:
	UPROPERTY(Transient)
	TObjectPtr<UMEPHeroWidget> HeroWidget;
};
