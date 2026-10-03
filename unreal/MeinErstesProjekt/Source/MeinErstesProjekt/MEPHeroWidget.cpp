#include "MEPHeroWidget.h"

#include "MEPFlowerActor.h"
#include "MEPFlowFieldActor.h"
#include "MEPThemeSubsystem.h"
#include "Blueprint/SlateBlueprintLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/ButtonSlot.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/SizeBox.h"
#include "Components/Spacer.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Engine/World.h"
#include "Styling/CoreStyle.h"

namespace
{
	const TCHAR* TitleString = TEXT("mein-erstes-projekt");
	const TCHAR* EyebrowString = TEXT("HALLO, WELT");
	const TCHAR* TaglineString =
		TEXT("Ein erster Schritt – tausend Teilchen, die dem Fluss folgen und deiner Maus ausweichen.");
	const TCHAR* PauseLabel = TEXT("Animation pausieren");
	const TCHAR* PlayLabel = TEXT("Animation abspielen");

	constexpr float Gap = 20.f;               // gap: 1.25rem
	constexpr float ShimmerSeconds = 10.f;    // animation: shimmer 10s … alternate
	const FVector2D FlowerSize(176.f, 290.f); // Platz für die Blume (Seitenverhältnis der SVG)

	// Abgerundete „Glas“-Fläche mit Kontur, wie border-radius: 999px.
	FSlateBrush MakePill(const FLinearColor& Fill, const FLinearColor& Outline)
	{
		FSlateBrush Brush;
		Brush.DrawAs = ESlateBrushDrawType::RoundedBox;
		Brush.TintColor = FSlateColor(Fill);
		Brush.OutlineSettings.RoundingType = ESlateBrushRoundingType::HalfHeightRadius;
		Brush.OutlineSettings.Color = FSlateColor(Outline);
		Brush.OutlineSettings.Width = 1.f;
		return Brush;
	}

	// linear-gradient(100deg, accent-1, accent-2 50%, accent-3)
	FLinearColor Gradient(const FMEPPalette& Palette, float U)
	{
		U = FMath::Clamp(U, 0.f, 1.f);
		return U < 0.5f
			? FMath::Lerp(Palette.Accent[0], Palette.Accent[1], U * 2.f)
			: FMath::Lerp(Palette.Accent[1], Palette.Accent[2], (U - 0.5f) * 2.f);
	}
}

void UMEPHeroWidget::SetSceneActors(AMEPFlowFieldActor* InFlowField, AMEPFlowerActor* InFlower)
{
	FlowField = InFlowField;
	Flower = InFlower;
	UpdateToggleLabel();
}

void UMEPHeroWidget::NativeOnInitialized()
{
	Super::NativeOnInitialized();
	BuildTree();
}

void UMEPHeroWidget::BuildTree()
{
	UCanvasPanel* Root = WidgetTree->ConstructWidget<UCanvasPanel>(UCanvasPanel::StaticClass(), TEXT("Root"));
	Root->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
	WidgetTree->RootWidget = Root;

	// Alles mittig untereinander, wie .hero (flex-direction: column; justify-content: center)
	UVerticalBox* Hero = WidgetTree->ConstructWidget<UVerticalBox>(UVerticalBox::StaticClass(), TEXT("Hero"));
	Hero->SetVisibility(ESlateVisibility::SelfHitTestInvisible);
	UCanvasPanelSlot* HeroSlot = Root->AddChildToCanvas(Hero);
	HeroSlot->SetAnchors(FAnchors(0.5f, 0.5f));
	HeroSlot->SetAlignment(FVector2D(0.5f, 0.5f));
	HeroSlot->SetPosition(FVector2D::ZeroVector);
	HeroSlot->SetAutoSize(true);

	auto AddRow = [Hero](UWidget* Widget, float BottomGap)
	{
		UVerticalBoxSlot* Row = Hero->AddChildToVerticalBox(Widget);
		Row->SetHorizontalAlignment(HAlign_Center);
		Row->SetPadding(FMargin(0.f, 0.f, 0.f, BottomGap));
	};

	// .eyebrow
	Eyebrow = WidgetTree->ConstructWidget<UBorder>(UBorder::StaticClass(), TEXT("Eyebrow"));
	Eyebrow->SetVisibility(ESlateVisibility::HitTestInvisible);
	Eyebrow->SetPadding(FMargin(14.f, 6.f));
	EyebrowText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("EyebrowText"));
	FSlateFontInfo EyebrowFont = FCoreStyle::GetDefaultFontStyle(TEXT("Bold"), 10);
	EyebrowFont.LetterSpacing = 140; // 0.14em
	EyebrowText->SetFont(EyebrowFont);
	EyebrowText->SetText(FText::FromString(EyebrowString));
	Eyebrow->SetContent(EyebrowText);
	AddRow(Eyebrow, Gap);

	// .title – ein Textblock pro Buchstabe, damit jeder seine Farbe aus dem Verlauf bekommt
	UHorizontalBox* Title = WidgetTree->ConstructWidget<UHorizontalBox>(UHorizontalBox::StaticClass(), TEXT("Title"));
	Title->SetVisibility(ESlateVisibility::HitTestInvisible);
	const FSlateFontInfo TitleFont = FCoreStyle::GetDefaultFontStyle(TEXT("Bold"), 72);
	for (const TCHAR Char : FString(TitleString))
	{
		UTextBlock* Letter = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass());
		Letter->SetFont(TitleFont);
		Letter->SetText(FText::FromString(FString::Chr(Char)));
		Title->AddChildToHorizontalBox(Letter);
		TitleLetters.Add(Letter);
	}
	AddRow(Title, Gap);

	// .tagline (max-width: 34rem)
	USizeBox* TaglineBox = WidgetTree->ConstructWidget<USizeBox>(USizeBox::StaticClass(), TEXT("TaglineBox"));
	TaglineBox->SetVisibility(ESlateVisibility::HitTestInvisible);
	TaglineBox->SetMaxDesiredWidth(544.f);
	Tagline = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("Tagline"));
	Tagline->SetFont(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"), 15));
	Tagline->SetText(FText::FromString(TaglineString));
	Tagline->SetJustification(ETextJustify::Center);
	Tagline->SetAutoWrapText(true);
	TaglineBox->SetContent(Tagline);
	AddRow(TaglineBox, Gap);

	// .flower – nur ein Platzhalter; die 3D-Blume wird in der Welt genau hierhin gestellt.
	FlowerSlot = WidgetTree->ConstructWidget<USpacer>(USpacer::StaticClass(), TEXT("FlowerSlot"));
	FlowerSlot->SetSize(FlowerSize);
	AddRow(FlowerSlot, Gap + 12.f);

	// .toggle
	ToggleButton = WidgetTree->ConstructWidget<UButton>(UButton::StaticClass(), TEXT("Toggle"));
	ToggleButton->OnClicked.AddDynamic(this, &UMEPHeroWidget::HandleToggleClicked);
	ToggleText = WidgetTree->ConstructWidget<UTextBlock>(UTextBlock::StaticClass(), TEXT("ToggleText"));
	ToggleText->SetFont(FCoreStyle::GetDefaultFontStyle(TEXT("Bold"), 11));
	if (UButtonSlot* ButtonSlot = Cast<UButtonSlot>(ToggleButton->AddChild(ToggleText)))
	{
		ButtonSlot->SetPadding(FMargin(21.f, 11.f));
	}
	AddRow(ToggleButton, 0.f);
}

void UMEPHeroWidget::NativeConstruct()
{
	Super::NativeConstruct();

	Theme = GetWorld() ? GetWorld()->GetSubsystem<UMEPThemeSubsystem>() : nullptr;
	if (Theme)
	{
		ThemeHandle = Theme->OnThemeChanged.AddUObject(this, &UMEPHeroWidget::ApplyTheme);
	}
	ApplyTheme();
	UpdateToggleLabel();
}

void UMEPHeroWidget::NativeDestruct()
{
	if (Theme)
	{
		Theme->OnThemeChanged.Remove(ThemeHandle);
	}
	Super::NativeDestruct();
}

void UMEPHeroWidget::ApplyTheme()
{
	const FMEPPalette Palette = Theme ? Theme->GetPalette() : FMEPPalette::Make(false);

	Eyebrow->SetBrush(MakePill(Palette.Glass, Palette.GlassBorder));
	EyebrowText->SetColorAndOpacity(FSlateColor(Palette.Muted));
	Tagline->SetColorAndOpacity(FSlateColor(Palette.Muted));
	ToggleText->SetColorAndOpacity(FSlateColor(Palette.Fg));

	FButtonStyle Style = ToggleButton->GetStyle();
	Style.SetNormal(MakePill(Palette.Glass, Palette.GlassBorder));
	Style.SetHovered(MakePill(Palette.Glass, Palette.Accent[0]));
	Style.SetPressed(MakePill(Palette.Glass * FLinearColor(0.9f, 0.9f, 0.9f, 1.f), Palette.Accent[0]));
	Style.SetNormalPadding(FMargin(0.f));
	Style.SetPressedPadding(FMargin(0.f));
	ToggleButton->SetStyle(Style);

	UpdateTitleColors();
}

void UMEPHeroWidget::UpdateTitleColors()
{
	const FMEPPalette Palette = Theme ? Theme->GetPalette() : FMEPPalette::Make(false);

	// Der Verlauf ist doppelt so breit wie der Titel (background-size: 200%) und wandert
	// hin und her. Mit reduzierter Bewegung steht er still.
	float Phase = 0.f;
	if (!(Theme && Theme->IsReducedMotion()))
	{
		const float Cycle = FMath::Fmod(ShimmerTime, 2.f * ShimmerSeconds) / ShimmerSeconds;
		const float PingPong = Cycle <= 1.f ? Cycle : 2.f - Cycle;
		Phase = 0.5f - 0.5f * FMath::Cos(UE_PI * PingPong); // ease-in-out
	}

	const int32 Count = TitleLetters.Num();
	for (int32 Index = 0; Index < Count; ++Index)
	{
		const float Position = Count > 1 ? float(Index) / (Count - 1) : 0.f;
		TitleLetters[Index]->SetColorAndOpacity(FSlateColor(Gradient(Palette, Position * 0.5f + Phase * 0.5f)));
	}
}

void UMEPHeroWidget::UpdateToggleLabel()
{
	if (!ToggleText)
	{
		return;
	}

	const bool bAnimating = FlowField.IsValid() ? FlowField->IsAnimating() : true;
	if (bLabelInitialized && bAnimating == bShownAnimating)
	{
		return;
	}
	bLabelInitialized = true;
	bShownAnimating = bAnimating;
	ToggleText->SetText(FText::FromString(bAnimating ? PauseLabel : PlayLabel));
}

void UMEPHeroWidget::HandleToggleClicked()
{
	if (FlowField.IsValid())
	{
		FlowField->TogglePaused();
	}
	UpdateToggleLabel();
}

void UMEPHeroWidget::UpdateFlowerPlacement()
{
	if (!Flower.IsValid() || !FlowerSlot)
	{
		return;
	}

	const FGeometry& Geometry = FlowerSlot->GetCachedGeometry();
	const FVector2D LocalSize = Geometry.GetLocalSize();
	if (LocalSize.X <= 0.0 || LocalSize.Y <= 0.0)
	{
		return;
	}

	FVector2D Top, Bottom, ViewportPosition;
	USlateBlueprintLibrary::LocalToViewport(this, Geometry, FVector2D(LocalSize.X * 0.5, 0.0), Top, ViewportPosition);
	USlateBlueprintLibrary::LocalToViewport(this, Geometry, FVector2D(LocalSize.X * 0.5, LocalSize.Y), Bottom, ViewportPosition);

	const float Height = float(Bottom.Y - Top.Y);
	if (Height > 1.f)
	{
		Flower->SetScreenRect((Top + Bottom) * 0.5, Height);
	}
}

void UMEPHeroWidget::NativeTick(const FGeometry& MyGeometry, float InDeltaTime)
{
	Super::NativeTick(MyGeometry, InDeltaTime);

	ShimmerTime += InDeltaTime;
	UpdateTitleColors();
	// Die Bewegungs-Einstellung des Systems kann sich ändern, ohne dass jemand klickt.
	UpdateToggleLabel();
	UpdateFlowerPlacement();
}
