#include "MEPFlowerActor.h"

#include "MEPShapes.h"
#include "MEPThemeSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	// Die SVG ist 200 × 300 groß; die Wiese ragt 28 Einheiten unter den Rand,
	// deshalb ist die Figur insgesamt 328 Einheiten hoch.
	constexpr float SvgWidth = 200.f;
	constexpr float FigureHeight = 328.f;
	constexpr float Thin = 0.02f;           // Dicke der flachen Formen (Kugel: 2 Einheiten)

	constexpr float GrowDuration = 1.1f;
	constexpr float SwayPeriod = 6.f;
	constexpr float SwayDegrees = 1.8f;

	// SVG-Koordinaten (y nach unten) -> lokale Koordinaten (Y nach rechts, Z nach oben,
	// Ursprung unten in der Mitte). Negatives X liegt näher an der Kamera.
	FVector Svg(double X, double Y, double Depth)
	{
		return FVector(Depth, X - SvgWidth * 0.5f, FigureHeight - Y);
	}

	// Drehung in der Bildebene; positive Grad wie CSS rotate() im Uhrzeigersinn.
	FQuat ScreenRotation(double Degrees)
	{
		return FQuat(FVector::XAxisVector, FMath::DegreesToRadians(-Degrees));
	}

	FVector CubicBezier(const FVector2D& P0, const FVector2D& P1, const FVector2D& P2, const FVector2D& P3, float T)
	{
		const double U = 1.0 - T;
		const FVector2D P = U * U * U * P0 + 3.0 * U * U * T * P1 + 3.0 * U * T * T * P2 + T * T * T * P3;
		return FVector(0.f, P.X, P.Y);
	}
}

AMEPFlowerActor::AMEPFlowerActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SceneRoot->SetMobility(EComponentMobility::Movable);
	RootComponent = SceneRoot;

	Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("Pivot"));
	Pivot->SetMobility(EComponentMobility::Movable);
	Pivot->SetupAttachment(SceneRoot);

	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cylinder(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	CubeMesh = Cube.Object;
	SphereMesh = Sphere.Object;
	CylinderMesh = Cylinder.Object;
}

void AMEPFlowerActor::BeginPlay()
{
	Super::BeginPlay();

	Theme = GetWorld()->GetSubsystem<UMEPThemeSubsystem>();
	if (!Theme)
	{
		return;
	}

	BuildFlower();
	ThemeHandle = Theme->OnThemeChanged.AddUObject(this, &AMEPFlowerActor::ApplyTheme);
	ApplyTheme();

	// Erst zeigen, wenn das UI den Platz für die Blume gemeldet hat.
	SetActorHiddenInGame(true);
}

void AMEPFlowerActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (Theme)
	{
		Theme->OnThemeChanged.Remove(ThemeHandle);
	}
	Super::EndPlay(EndPlayReason);
}

void AMEPFlowerActor::AddPart(UStaticMesh* Mesh, const FString& Hex, double SvgX, double SvgY, double Depth,
	const FVector& Size, double RollRadians)
{
	AddPart(Mesh, Hex, SvgX, SvgY, Depth, Size, FQuat(FVector::XAxisVector, RollRadians));
}

void AMEPFlowerActor::AddPart(UStaticMesh* Mesh, const FString& Hex, double SvgX, double SvgY, double Depth,
	const FVector& Size, const FQuat& Rotation)
{
	const FLinearColor Color(FColor::FromHex(Hex));
	UMaterialInstanceDynamic* Material = Theme->MakeColorMaterial(this, Color);
	// Alle Grundformen der Engine sind 100 Einheiten groß, Size ist in SVG-Einheiten.
	MEP::AddShape(this, Pivot, Mesh, Material, FTransform(Rotation, Svg(SvgX, SvgY, Depth), Size / 100.f));
	PartMaterials.Add(Material);
	PartColors.Add(Color);
}

void AMEPFlowerActor::BuildFlower()
{
	const float Flat = Thin * 100.f;

	// Himmel und Wiese
	AddPart(CubeMesh, TEXT("e8f6ff"), 100.f, FigureHeight * 0.5f, 0.f, FVector(Flat, SvgWidth, FigureHeight));
	AddPart(SphereMesh, TEXT("8fd16a"), 100.f, 300.f, -6.f, FVector(Flat, SvgWidth, 56.f));

	// Stiel: kubische Bézierkurve „M100 110 C 96 170, 106 220, 100 290“ aus Zylinderstücken
	{
		const FVector2D P0(100.f, -110.f), P1(96.f, -170.f), P2(106.f, -220.f), P3(100.f, -290.f);
		constexpr int32 Segments = 8;
		constexpr float StemWidth = 7.f;
		for (int32 Index = 0; Index < Segments; ++Index)
		{
			const FVector A = CubicBezier(P0, P1, P2, P3, float(Index) / Segments);
			const FVector B = CubicBezier(P0, P1, P2, P3, float(Index + 1) / Segments);
			const FVector Mid = (A + B) * 0.5f;
			const FVector Dir = (B - A).GetSafeNormal();
			const FQuat Rotation = FQuat::FindBetweenNormals(FVector::UpVector, Dir);
			AddPart(CylinderMesh, TEXT("3f9b3a"), Mid.Y, -Mid.Z, -10.f,
				FVector(StemWidth, StemWidth, FVector::Dist(A, B) + 1.f), Rotation);
			// Runde Gelenke wie stroke-linecap: round
			AddPart(SphereMesh, TEXT("3f9b3a"), B.Y, -B.Z, -10.f, FVector(StemWidth));
		}
		AddPart(SphereMesh, TEXT("3f9b3a"), P0.X, -P0.Y, -10.f, FVector(StemWidth));
	}

	// Blätter mit Mittelrippe
	struct FLeaf { FVector2D From, To; };
	const FLeaf Leaves[] = {
		{ FVector2D(101.f, 215.f), FVector2D(172.f, 205.f) },
		{ FVector2D(99.f, 245.f), FVector2D(28.f, 235.f) },
	};
	for (const FLeaf& Leaf : Leaves)
	{
		const FVector2D Center = (Leaf.From + Leaf.To) * 0.5f;
		const double Length = FVector2D::Distance(Leaf.From, Leaf.To);
		// Winkel in der Bildebene (Z nach oben, deshalb y umdrehen).
		const double Angle = FMath::Atan2(-(Leaf.To.Y - Leaf.From.Y), Leaf.To.X - Leaf.From.X);
		AddPart(SphereMesh, TEXT("5cbf4a"), Center.X, Center.Y, -12.f, FVector(Flat, Length, 28.f), Angle);
		AddPart(CubeMesh, TEXT("3f9b3a"), Center.X, Center.Y, -14.f, FVector(Flat, Length * 0.9f, 2.f), Angle);
	}

	// Blütenblätter: acht Ellipsen (rx 18, ry 32) im Abstand 38 um (100, 100),
	// dahinter je eine etwas größere als Kontur (stroke #e0507a).
	const FVector2D FlowerCenter(100.f, 100.f);
	for (int32 Index = 0; Index < 8; ++Index)
	{
		const double Degrees = Index * 45.0;
		const double Radians = FMath::DegreesToRadians(Degrees);
		const double X = FlowerCenter.X + 38.0 * FMath::Sin(Radians);
		const double Y = FlowerCenter.Y - 38.0 * FMath::Cos(Radians);
		const FQuat Rotation = ScreenRotation(Degrees);
		AddPart(SphereMesh, TEXT("e0507a"), X, Y, -16.f, FVector(Flat, 38.f, 66.f), Rotation);
		AddPart(SphereMesh, Index % 2 == 0 ? TEXT("ff7aa2") : TEXT("ff8fb1"), X, Y, -18.0 - Index * 0.5,
			FVector(Flat, 36.f, 64.f), Rotation);
	}

	// Blütenmitte mit Kontur und Samen
	AddPart(SphereMesh, TEXT("e8a317"), 100.f, 100.f, -24.f, FVector(Flat, 47.f, 47.f));
	AddPart(SphereMesh, TEXT("ffd23f"), 100.f, 100.f, -26.f, FVector(Flat, 41.f, 41.f));
	const FVector2D Seeds[] = {
		FVector2D(93.f, 94.f), FVector2D(106.f, 93.f), FVector2D(100.f, 102.f),
		FVector2D(91.f, 107.f), FVector2D(109.f, 106.f),
	};
	for (const FVector2D& Seed : Seeds)
	{
		AddPart(SphereMesh, TEXT("e8a317"), Seed.X, Seed.Y, -28.f, FVector(Flat, 5.f, 5.f));
	}
}

void AMEPFlowerActor::ApplyTheme()
{
	// filter: brightness(var(--flower-dim))
	const float Dim = Theme->GetPalette().FlowerDim;
	for (int32 Index = 0; Index < PartMaterials.Num(); ++Index)
	{
		UMEPThemeSubsystem::SetColor(PartMaterials[Index], PartColors[Index] * Dim);
	}
}

void AMEPFlowerActor::SetScreenRect(const FVector2D& CenterPixels, float HeightPixels)
{
	float SceneW, SceneH;
	FVector2D ViewportSize;
	MEP::GetSceneSize(GetWorld(), SceneW, SceneH, &ViewportSize);

	const float WorldHeight = HeightPixels / float(ViewportSize.Y) * SceneH;
	FigureScale = WorldHeight / FigureHeight;

	FVector Location = MEP::ViewportToScene(GetWorld(), CenterPixels, GetActorLocation().X);
	Location.Z -= WorldHeight * 0.5f;
	SetActorLocation(Location);

	if (!bHasScreenRect)
	{
		bHasScreenRect = true;
		AnimTime = 0.f;
		SetActorHiddenInGame(false);
	}
}

void AMEPFlowerActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	float Scale = 1.f;
	float Degrees = 0.f;

	if (bHasScreenRect && Theme && !Theme->IsReducedMotion())
	{
		AnimTime += DeltaSeconds;
		if (AnimTime < GrowDuration)
		{
			// flower-grow: scale(0.6) rotate(-4deg) -> scale(1) rotate(0), weich auslaufend
			const float T = AnimTime / GrowDuration;
			const float Ease = 1.f - FMath::Pow(1.f - T, 3.f);
			Scale = FMath::Lerp(0.6f, 1.f, Ease);
			Degrees = FMath::Lerp(-4.f, 0.f, Ease);
		}
		else
		{
			// flower-sway: sanftes Pendeln um ±1,8°
			const float SwayTime = AnimTime - GrowDuration;
			Degrees = SwayDegrees * FMath::Sin(2.f * UE_PI * SwayTime / SwayPeriod);
		}
	}

	Pivot->SetRelativeScale3D(FVector(1.f, Scale * FigureScale, Scale * FigureScale));
	Pivot->SetRelativeRotation(ScreenRotation(Degrees));
}
