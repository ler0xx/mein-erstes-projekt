#include "MEPBackdropActor.h"

#include "MEPShapes.h"
#include "MEPThemeSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 NumRings = 18;
	constexpr float GradientEnd = 0.7f;   // „var(--bg) 70%“
	constexpr float RingSpacing = 4.f;    // Abstand der Scheiben in Blickrichtung
}

AMEPBackdropActor::AMEPBackdropActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SceneRoot->SetMobility(EComponentMobility::Movable);
	RootComponent = SceneRoot;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	CubeMesh = Cube.Object;
	CylinderMesh = Cylinder.Object;
}

void AMEPBackdropActor::BeginPlay()
{
	Super::BeginPlay();

	Theme = GetWorld()->GetSubsystem<UMEPThemeSubsystem>();
	if (!Theme)
	{
		return;
	}

	// Große Grundfläche ganz hinten.
	UMaterialInstanceDynamic* BaseMaterial = Theme->MakeColorMaterial(this, FLinearColor::White);
	Base = MEP::AddShape(this, SceneRoot, CubeMesh, BaseMaterial,
		FTransform(FQuat::Identity, FVector(NumRings * RingSpacing + 20.f, 0.f, 0.f), FVector(0.01f, 100.f, 100.f)));
	Materials.Add(BaseMaterial);

	// Scheiben von außen (groß, hinten) nach innen (klein, vorne).
	for (int32 Index = 0; Index < NumRings; ++Index)
	{
		UMaterialInstanceDynamic* Material = Theme->MakeColorMaterial(this, FLinearColor::White);
		UStaticMeshComponent* Ring = MEP::AddShape(this, SceneRoot, CylinderMesh, Material,
			FTransform(FRotator(90.f, 0.f, 0.f), FVector((NumRings - Index) * RingSpacing, 0.f, 0.f)));
		Rings.Add(Ring);
		Materials.Add(Material);
	}

	ThemeHandle = Theme->OnThemeChanged.AddUObject(this, &AMEPBackdropActor::ApplyTheme);
	ApplyTheme();
	UpdateLayout();
}

void AMEPBackdropActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (Theme)
	{
		Theme->OnThemeChanged.Remove(ThemeHandle);
	}
	Super::EndPlay(EndPlayReason);
}

void AMEPBackdropActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	UpdateLayout();
}

void AMEPBackdropActor::ApplyTheme()
{
	const FMEPPalette& Palette = Theme->GetPalette();
	UMEPThemeSubsystem::SetColor(Materials[0], Palette.Bg);

	for (int32 Index = 0; Index < NumRings; ++Index)
	{
		// Mitte des Rings als Anteil des Verlaufs: 1 = außen (--bg), 0 = Zentrum (--bg-glow).
		const float T = (NumRings - Index - 0.5f) / NumRings;
		UMEPThemeSubsystem::SetColor(Materials[Index + 1], FMath::Lerp(Palette.BgGlow, Palette.Bg, T));
	}
}

void AMEPBackdropActor::UpdateLayout()
{
	float Width, Height;
	MEP::GetSceneSize(GetWorld(), Width, Height);
	if (FMath::IsNearlyEqual(Height, LastHeight) || Rings.Num() == 0)
	{
		return;
	}
	LastHeight = Height;

	// „ellipse at 50% 40%“ mit farthest-corner: Halbachsen = √2 × Abstand zum fernsten Rand.
	const float RadiusY = Width * 0.5f * UE_SQRT_2 * GradientEnd;
	const float RadiusZ = Height * 0.6f * UE_SQRT_2 * GradientEnd;
	const float CenterZ = Height * 0.5f - Height * 0.4f;

	for (int32 Index = 0; Index < NumRings; ++Index)
	{
		const float Fraction = float(NumRings - Index) / NumRings;
		UStaticMeshComponent* Ring = Rings[Index];
		FVector Location = Ring->GetRelativeLocation();
		Location.Z = CenterZ;
		Ring->SetRelativeLocation(Location);

		// Der Zylinder ist um 90° gekippt: lokales X zeigt nach oben, lokales Y nach rechts.
		Ring->SetRelativeScale3D(FVector(2.f * RadiusZ * Fraction / 100.f, 2.f * RadiusY * Fraction / 100.f, 0.01f));
	}
}
