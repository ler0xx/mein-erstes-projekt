#include "AgentCharacter.h"

#include "AgentOffice.h"
#include "Animation/AnimSequenceBase.h"
#include "Animation/AnimationAsset.h"
#include "Components/RectLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/WidgetComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Framework/Application/SlateApplication.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace AgentLook
{
	// Platzhalter aus dem Engine-Content (kein Zusatz-Download nötig)
	static const TCHAR* PlaceholderMesh = TEXT("/Engine/Tutorial/SubEditors/TutorialAssets/Character/TutorialTPP.TutorialTPP");
	static const TCHAR* PlaceholderIdle = TEXT("/Engine/Tutorial/SubEditors/TutorialAssets/Character/Tutorial_Idle.Tutorial_Idle");
	// Graubox-Material aus Scripts/build_level.py – dort für Skeletal Meshes freigegeben
	// (BasicShapeMaterial aus der Engine ist das nicht; im Spiel käme dann nur das Default-Material)
	static const TCHAR* TintMaterial = TEXT("/Game/Graybox/Materials/M_Graybox.M_Graybox");
	static const FName TintColorParameter(TEXT("BaseColor"));

	// Zurückhaltende Farben – kein Comic-Look
	static const FLinearColor PlateBackground(0.010f, 0.010f, 0.012f, 0.80f);
	static const FLinearColor NameColor(0.92f, 0.92f, 0.90f, 1.f);
	static const FLinearColor TaskColor(0.62f, 0.62f, 0.60f, 1.f);
	static const FLinearColor WorkingColor(0.16f, 0.42f, 0.26f, 1.f);
	static const FLinearColor WaitingColor(0.30f, 0.30f, 0.30f, 1.f);

	/** Agentenfarbe stark entsättigt und abgedunkelt – nur als feiner Akzent. */
	static FLinearColor Muted(const FLinearColor& Color)
	{
		FLinearColor HSV = Color.LinearRGBToHSV();
		HSV.G *= 0.45f;                       // Sättigung
		HSV.B = FMath::Min(HSV.B, 0.5f);      // Helligkeit
		FLinearColor Out = HSV.HSVToLinearRGB();
		Out.A = 1.f;
		return Out;
	}

	static FText Shorten(const FString& Text, int32 MaxChars)
	{
		if (Text.Len() <= MaxChars)
		{
			return FText::FromString(Text);
		}
		return FText::FromString(Text.Left(MaxChars - 1).TrimEnd() + TEXT("\u2026"));
	}
}

AAgentCharacter::AAgentCharacter()
{
	PrimaryActorTick.bCanEverTick = false;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SceneRoot->SetMobility(EComponentMobility::Movable);
	RootComponent = SceneRoot;

	Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(SceneRoot);
	Body->SetRelativeRotation(FRotator(0.f, BodyMeshYaw, 0.f));
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->SetCastShadow(true);

	ScreenLight = CreateDefaultSubobject<URectLightComponent>(TEXT("ScreenLight"));
	ScreenLight->SetupAttachment(SceneRoot);
	// Vor dem Monitor (Person sitzt 75 cm hinter der Tischmitte, Monitor ~28 cm hinter der Mitte); strahlt zurück zur Person
	ScreenLight->SetRelativeLocation(FVector(98.f, 0.f, 105.f));
	ScreenLight->SetRelativeRotation(FRotator(10.f, 180.f, 0.f));
	ScreenLight->IntensityUnits = ELightUnits::Lumens;
	ScreenLight->Intensity = 0.f;
	ScreenLight->bUseTemperature = true;
	ScreenLight->Temperature = 6500.f;
	ScreenLight->SourceWidth = 55.f;
	ScreenLight->SourceHeight = 32.f;
	ScreenLight->AttenuationRadius = 350.f;
	ScreenLight->CastShadows = false;

	NamePlate = CreateDefaultSubobject<UWidgetComponent>(TEXT("NamePlate"));
	NamePlate->SetupAttachment(SceneRoot);
	NamePlate->SetRelativeLocation(FVector(0.f, 0.f, 205.f));
	NamePlate->SetWidgetSpace(EWidgetSpace::Screen);
	NamePlate->SetDrawAtDesiredSize(true);
	NamePlate->SetPivot(FVector2D(0.5f, 1.f));
	NamePlate->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	BodyMesh = TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(AgentLook::PlaceholderMesh));
	WorkingAnimation = TSoftObjectPtr<UAnimationAsset>(FSoftObjectPath(AgentLook::PlaceholderIdle));
}

void AAgentCharacter::BeginPlay()
{
	Super::BeginPlay();

	Body->SetRelativeRotation(FRotator(0.f, BodyMeshYaw, 0.f));
	if (!Body->GetSkeletalMeshAsset() && !BodyMesh.IsNull())
	{
		const bool bIsPlaceholder = BodyMesh.ToSoftObjectPath() == FSoftObjectPath(AgentLook::PlaceholderMesh);
		ApplyBodyMesh(BodyMesh.LoadSynchronous(), bIsPlaceholder);
	}

	BuildNamePlate();
	UpdateAnimation(/*bRestart*/ true);
	UpdateScreenLight();
	UpdateNamePlate();

	if (bHasWorker)
	{
		OnWorkerUpdated(Worker, /*bWorkingChanged*/ true);
	}
}

void AAgentCharacter::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (NamePlate)
	{
		NamePlate->SetSlateWidget(nullptr);
	}
	NameText.Reset();
	TaskText.Reset();
	StatusText.Reset();
	AccentBar.Reset();
	StatusDot.Reset();

	Super::EndPlay(EndPlayReason);
}

void AAgentCharacter::ApplyWorker(const FOfficeWorker& InWorker)
{
	const bool bWorkingChanged = !bHasWorker || Worker.bWorking != InWorker.bWorking;
	Worker = InWorker;
	bHasWorker = true;

	if (HasActorBegunPlay())
	{
		UpdateAnimation(/*bRestart*/ false);
		UpdateScreenLight();
		UpdateNamePlate();
		OnWorkerUpdated(Worker, bWorkingChanged);
	}
}

void AAgentCharacter::SetSpotType(const FString& InSpotType)
{
	SpotType = InSpotType;
	if (HasActorBegunPlay())
	{
		UpdateScreenLight();
	}
}

void AAgentCharacter::SetBodyMesh(USkeletalMesh* NewMesh)
{
	if (!NewMesh)
	{
		return;
	}
	ApplyBodyMesh(NewMesh, /*bIsPlaceholder*/ false);
	UpdateAnimation(/*bRestart*/ true);
}

void AAgentCharacter::ApplyBodyMesh(USkeletalMesh* Mesh, bool bIsPlaceholder)
{
	if (!Mesh)
	{
		UE_LOG(LogAgentOffice, Warning, TEXT("Agent: Skeletal Mesh konnte nicht geladen werden."));
		return;
	}

	Body->SetSkeletalMeshAsset(Mesh);
	Body->EmptyOverrideMaterials();
	PlayingAnimation.Reset();

	if (bIsPlaceholder && bTintPlaceholder)
	{
		// Das graue Mannequin dunkel einfärben – deutet bis zu den MetaHumans den dunklen Anzug an
		UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, AgentLook::TintMaterial, nullptr, LOAD_NoWarn);
		if (!Base || !Base->GetUsageByFlag(MATUSAGE_SkeletalMesh))
		{
			static bool bWarned = false;
			if (!bWarned)
			{
				UE_LOG(LogAgentOffice, Warning, TEXT("Agent: %s fehlt oder ist nicht für Skeletal Meshes freigegeben – Figuren bleiben ungefärbt. Scripts/build_level.py ausführen."), AgentLook::TintMaterial);
				bWarned = true;
			}
		}
		else
		{
			UMaterialInstanceDynamic* Suit = UMaterialInstanceDynamic::Create(Base, this);
			Suit->SetVectorParameterValue(AgentLook::TintColorParameter, PlaceholderSuitColor);
			for (int32 Slot = 0; Slot < Body->GetNumMaterials(); ++Slot)
			{
				Body->SetMaterial(Slot, Suit);
			}
		}
	}
}

void AAgentCharacter::UpdateAnimation(bool bRestart)
{
	USkeletalMesh* Mesh = Body->GetSkeletalMeshAsset();
	if (!Mesh)
	{
		return;
	}

	const bool bUseWaitingAnim = !Worker.bWorking && !WaitingAnimation.IsNull();
	UAnimationAsset* Wanted = bUseWaitingAnim ? WaitingAnimation.LoadSynchronous() : WorkingAnimation.LoadSynchronous();

	// Passt die Animation nicht zum Skelett (z. B. MetaHuman + Mannequin-Animation), überlassen wir das dem Anim-Blueprint
	if (!Wanted || Wanted->GetSkeleton() != Mesh->GetSkeleton())
	{
		return;
	}

	if (bRestart || PlayingAnimation.Get() != Wanted)
	{
		Body->PlayAnimation(Wanted, /*bLooping*/ true);
		// Zufälliger Startpunkt, damit nicht alle Agenten im Gleichtakt atmen
		if (const UAnimSequenceBase* Sequence = Cast<UAnimSequenceBase>(Wanted))
		{
			Body->SetPosition(FMath::FRandRange(0.f, Sequence->GetPlayLength()), /*bFireNotifies*/ false);
		}
		PlayingAnimation = Wanted;
	}

	Body->SetPlayRate(Worker.bWorking ? WorkingPlayRate : WaitingPlayRate);
}

void AAgentCharacter::UpdateScreenLight()
{
	// Nur am Schreibtisch gibt es einen Monitor
	const bool bAtDesk = SpotType.Equals(TEXT("desk"), ESearchCase::IgnoreCase);
	const float Lumens = !bAtDesk ? 0.f : (Worker.bWorking ? ScreenLightWorkingLumens : ScreenLightWaitingLumens);

	ScreenLight->SetIntensityUnits(ELightUnits::Lumens);
	ScreenLight->SetIntensity(Lumens);
	ScreenLight->SetVisibility(Lumens > 0.f);
}

void AAgentCharacter::BuildNamePlate()
{
	if (!NamePlate || !FSlateApplication::IsInitialized())
	{
		return;
	}

	const FSlateBrush* White = FCoreStyle::Get().GetBrush(TEXT("WhiteBrush"));

	TSharedRef<SWidget> Plate =
		SNew(SBorder)
		.BorderImage(White)
		.BorderBackgroundColor(AgentLook::PlateBackground)
		.Padding(FMargin(0.f))
		[
			SNew(SHorizontalBox)
			+ SHorizontalBox::Slot()
			.AutoWidth()
			[
				SNew(SBox)
				.WidthOverride(3.f)
				[
					SAssignNew(AccentBar, SImage)
					.Image(White)
				]
			]
			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(FMargin(10.f, 6.f, 12.f, 7.f))
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SAssignNew(NameText, STextBlock)
					.Font(FCoreStyle::GetDefaultFontStyle(TEXT("Bold"), 12))
					.ColorAndOpacity(AgentLook::NameColor)
				]
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(FMargin(0.f, 1.f, 0.f, 0.f))
				[
					SAssignNew(TaskText, STextBlock)
					.Font(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"), 9))
					.ColorAndOpacity(AgentLook::TaskColor)
				]
				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(FMargin(0.f, 4.f, 0.f, 0.f))
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.VAlign(VAlign_Center)
					.Padding(FMargin(0.f, 0.f, 5.f, 0.f))
					[
						SNew(SBox)
						.WidthOverride(6.f)
						.HeightOverride(6.f)
						[
							SAssignNew(StatusDot, SImage)
							.Image(White)
						]
					]
					+ SHorizontalBox::Slot()
					.AutoWidth()
					.VAlign(VAlign_Center)
					[
						SAssignNew(StatusText, STextBlock)
						.Font(FCoreStyle::GetDefaultFontStyle(TEXT("Regular"), 8))
						.ColorAndOpacity(AgentLook::TaskColor)
					]
				]
			]
		];

	NamePlate->SetSlateWidget(Plate);
}

void AAgentCharacter::UpdateNamePlate()
{
	if (!NameText.IsValid())
	{
		return;
	}

	NameText->SetText(AgentLook::Shorten(Worker.Name, 32));
	TaskText->SetText(Worker.TaskName.IsEmpty() ? FText::FromString(TEXT("\u2013")) : AgentLook::Shorten(Worker.TaskName, 56));
	StatusText->SetText(FText::FromString(Worker.bWorking ? TEXT("arbeitet") : TEXT("wartet")));
	StatusDot->SetColorAndOpacity(Worker.bWorking ? AgentLook::WorkingColor : AgentLook::WaitingColor);
	AccentBar->SetColorAndOpacity(AgentLook::Muted(Worker.Color));
}
