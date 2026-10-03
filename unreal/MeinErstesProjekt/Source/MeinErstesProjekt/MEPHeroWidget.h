#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "MEPHeroWidget.generated.h"

class UBorder;
class UButton;
class USpacer;
class UTextBlock;
class AMEPFlowFieldActor;
class AMEPFlowerActor;
class UMEPThemeSubsystem;

/**
 * Der <main class="hero">-Block der Website als UMG-Widget, komplett in C++ aufgebaut
 * (kein Widget-Blueprint): Pille „Hallo, Welt“, Titel mit wanderndem Farbverlauf,
 * Untertitel, ein Platzhalter für die 3D-Blume und der Pause-/Abspielen-Button.
 */
UCLASS()
class UMEPHeroWidget : public UUserWidget
{
	GENERATED_BODY()

public:
	void SetSceneActors(AMEPFlowFieldActor* InFlowField, AMEPFlowerActor* InFlower);

protected:
	virtual void NativeOnInitialized() override;
	virtual void NativeConstruct() override;
	virtual void NativeDestruct() override;
	virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;

private:
	UFUNCTION()
	void HandleToggleClicked();

	void BuildTree();
	void ApplyTheme();
	void UpdateTitleColors();
	void UpdateToggleLabel();
	void UpdateFlowerPlacement();

	UPROPERTY(Transient)
	TObjectPtr<UBorder> Eyebrow;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> EyebrowText;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UTextBlock>> TitleLetters;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> Tagline;

	UPROPERTY(Transient)
	TObjectPtr<USpacer> FlowerSlot;

	UPROPERTY(Transient)
	TObjectPtr<UButton> ToggleButton;

	UPROPERTY(Transient)
	TObjectPtr<UTextBlock> ToggleText;

	UPROPERTY(Transient)
	TObjectPtr<UMEPThemeSubsystem> Theme;

	TWeakObjectPtr<AMEPFlowFieldActor> FlowField;
	TWeakObjectPtr<AMEPFlowerActor> Flower;

	FDelegateHandle ThemeHandle;
	float ShimmerTime = 0.f;
	bool bShownAnimating = true;
	bool bLabelInitialized = false;
};
