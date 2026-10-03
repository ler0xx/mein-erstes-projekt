#include "MEPFlowFieldActor.h"

#include "MEPThemeSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	constexpr int32 NumLayers = 3;          // eine Ebene pro Akzentfarbe
	constexpr float Speed = 0.9f;           // wie „speed“ in main.js
	constexpr float Opacity = 0.75f;        // globalAlpha der Striche
	constexpr float TrailFrames = 10.f;     // Länge des Strichs in Frames Bewegung
	constexpr float Thickness = 1.6f;       // Strichbreite relativ zu „size“
}

AMEPFlowFieldActor::AMEPFlowFieldActor()
{
	PrimaryActorTick.bCanEverTick = true;

	SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	SceneRoot->SetMobility(EComponentMobility::Movable);
	RootComponent = SceneRoot;

	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeMesh(TEXT("/Engine/BasicShapes/Cube.Cube"));

	for (int32 Index = 0; Index < NumLayers; ++Index)
	{
		UInstancedStaticMeshComponent* Layer = CreateDefaultSubobject<UInstancedStaticMeshComponent>(
			*FString::Printf(TEXT("Partikel%d"), Index + 1));
		Layer->SetupAttachment(SceneRoot);
		Layer->SetMobility(EComponentMobility::Movable);
		Layer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Layer->SetGenerateOverlapEvents(false);
		Layer->SetCastShadow(false);
		if (CubeMesh.Succeeded())
		{
			Layer->SetStaticMesh(CubeMesh.Object);
		}
		Layers.Add(Layer);
	}
}

void AMEPFlowFieldActor::BeginPlay()
{
	Super::BeginPlay();

	Theme = GetWorld()->GetSubsystem<UMEPThemeSubsystem>();
	LayerTransforms.SetNum(NumLayers);

	for (UInstancedStaticMeshComponent* Layer : Layers)
	{
		UMaterialInstanceDynamic* Material = Theme ? Theme->MakeColorMaterial(this, FLinearColor::White) : nullptr;
		LayerMaterials.Add(Material);
		if (Material)
		{
			Layer->SetMaterial(0, Material);
		}
	}

	if (Theme)
	{
		ThemeHandle = Theme->OnThemeChanged.AddUObject(this, &AMEPFlowFieldActor::ApplyTheme);
	}
	ApplyTheme();

	MEP::GetSceneSize(GetWorld(), Width, Height);
	EnsureParticleCount();
	UpdateInstances(IsAnimating());
}

void AMEPFlowFieldActor::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (Theme)
	{
		Theme->OnThemeChanged.Remove(ThemeHandle);
	}
	Super::EndPlay(EndPlayReason);
}

bool AMEPFlowFieldActor::IsAnimating() const
{
	if (UserChoice != EUserChoice::None)
	{
		return UserChoice == EUserChoice::Play;
	}
	return !(Theme && Theme->IsReducedMotion());
}

void AMEPFlowFieldActor::TogglePaused()
{
	UserChoice = IsAnimating() ? EUserChoice::Pause : EUserChoice::Play;
}

void AMEPFlowFieldActor::ApplyTheme()
{
	if (!Theme)
	{
		return;
	}

	// Die Striche sind auf der Website zu 75 % deckend; hier wird die Farbe vorab
	// mit dem Hintergrund gemischt, weil das Material deckend ist.
	const FMEPPalette& Palette = Theme->GetPalette();
	for (int32 Index = 0; Index < LayerMaterials.Num(); ++Index)
	{
		const FLinearColor Color = FMath::Lerp(Palette.Bg, Palette.Accent[Index % 3], Opacity);
		UMEPThemeSubsystem::SetColor(LayerMaterials[Index], Color);
	}
}

void AMEPFlowFieldActor::Spawn(FParticle& P) const
{
	P.X = FMath::FRand() * Width;
	P.Y = FMath::FRand() * Height;
	P.VX = 0.f;
	P.VY = 0.f;
	P.Life = 120.f + FMath::FRand() * 280.f;
	P.Size = 0.6f + FMath::FRand() * 1.4f;
}

float AMEPFlowFieldActor::FieldAngle(float X, float Y, float T) const
{
	// Perlin-Noise statt der geschichteten Sinuswellen aus main.js. Das Ergebnis
	// liegt etwa in [-1, 1]; großzügig skaliert ergibt es weiche Wirbel.
	constexpr float Scale = 0.0018f;
	const float Noise = FMath::PerlinNoise3D(FVector(X * Scale, Y * Scale, T * 0.004f));
	return Noise * 2.f * UE_PI * 1.6f;
}

void AMEPFlowFieldActor::EnsureParticleCount()
{
	// Mit der Fläche skalieren, aber begrenzt – wie particleCount() in main.js.
	const int32 Target = FMath::Clamp(FMath::RoundToInt(Width * Height / 1400.f), 250, 1400);
	if (Particles.Num() == Target)
	{
		return;
	}

	const int32 OldCount = Particles.Num();
	Particles.SetNum(Target);
	for (int32 Index = OldCount; Index < Target; ++Index)
	{
		Particles[Index].Group = FMath::RandRange(0, NumLayers - 1);
		Spawn(Particles[Index]);
	}

	// Instanzen neu anlegen; die Transformationen setzt UpdateInstances().
	TArray<int32> Counts;
	Counts.SetNumZeroed(NumLayers);
	for (const FParticle& P : Particles)
	{
		++Counts[P.Group];
	}
	for (int32 Layer = 0; Layer < NumLayers; ++Layer)
	{
		TArray<FTransform> Initial;
		Initial.Init(FTransform::Identity, Counts[Layer]);
		Layers[Layer]->ClearInstances();
		Layers[Layer]->AddInstances(Initial, false);
	}
}

bool AMEPFlowFieldActor::GetPointer(FVector2D& OutPointer) const
{
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	float MouseX = 0.f;
	float MouseY = 0.f;
	if (!PC || !PC->GetMousePosition(MouseX, MouseY))
	{
		return false;
	}

	float SceneW, SceneH;
	FVector2D ViewportSize;
	MEP::GetSceneSize(GetWorld(), SceneW, SceneH, &ViewportSize);
	if (MouseX < 0.f || MouseY < 0.f || MouseX > ViewportSize.X || MouseY > ViewportSize.Y)
	{
		return false;
	}

	OutPointer.X = MouseX / ViewportSize.X * SceneW;
	OutPointer.Y = MouseY / ViewportSize.Y * SceneH;
	return true;
}

void AMEPFlowFieldActor::Step(float Dt)
{
	Time += Dt * 0.6f;

	const float Radius = FMath::Min(180.f, FMath::Max(Width, Height) * 0.15f);
	const float Radius2 = Radius * Radius;
	const float Damping = FMath::Pow(0.92f, Dt);

	FVector2D Pointer;
	const bool bPointer = GetPointer(Pointer);

	for (FParticle& P : Particles)
	{
		const float Angle = FieldAngle(P.X, P.Y, Time);
		P.VX += FMath::Cos(Angle) * 0.12f * Dt;
		P.VY += FMath::Sin(Angle) * 0.12f * Dt;

		if (bPointer)
		{
			const float DX = P.X - Pointer.X;
			const float DY = P.Y - Pointer.Y;
			const float D2 = DX * DX + DY * DY;
			if (D2 < Radius2 && D2 > 0.01f)
			{
				const float D = FMath::Sqrt(D2);
				const float Force = (1.f - D / Radius) * 1.6f * Dt;
				P.VX += DX / D * Force;
				P.VY += DY / D * Force;
			}
		}

		P.VX *= Damping;
		P.VY *= Damping;
		P.X += P.VX * Speed * Dt;
		P.Y += P.VY * Speed * Dt;
		P.Life -= Dt;

		if (P.Life <= 0.f || P.X < -10.f || P.X > Width + 10.f || P.Y < -10.f || P.Y > Height + 10.f)
		{
			Spawn(P);
		}
	}
}

void AMEPFlowFieldActor::UpdateInstances(bool bMoving)
{
	for (TArray<FTransform>& Transforms : LayerTransforms)
	{
		Transforms.Reset();
	}

	for (const FParticle& P : Particles)
	{
		// Ausblenden am Lebensende: auf der Website über die Deckkraft, hier über die Breite.
		const float Fade = FMath::Clamp(P.Life / 60.f, 0.f, 1.f);

		// Bildschirm -> Bildebene: y zeigt nach unten, Welt-Z nach oben.
		const FVector Position(0.f, P.X - Width * 0.5f, Height * 0.5f - P.Y);

		float Length;
		float Thick;
		float Angle = 0.f;
		FVector Offset = FVector::ZeroVector;

		if (bMoving)
		{
			// Ein Strich vom Partikel nach hinten, so lang wie seine letzten Bewegungen –
			// das ersetzt die verblassenden Spuren des Canvas.
			const float WorldVY = P.VX;
			const float WorldVZ = -P.VY;
			const float PixelsPerFrame = FMath::Sqrt(WorldVY * WorldVY + WorldVZ * WorldVZ) * Speed;
			Length = FMath::Max(P.Size * 2.f, PixelsPerFrame * TrailFrames);
			Thick = P.Size * Thickness * Fade;
			Angle = FMath::Atan2(WorldVZ, WorldVY);
			Offset = FVector(0.f, -FMath::Cos(Angle), -FMath::Sin(Angle)) * (Length * 0.5f);
		}
		else
		{
			// Pausiert: ruhige Punkte wie drawStatic().
			Length = P.Size * 2.f;
			Thick = P.Size * 2.f * Fade;
		}

		// Der Würfel der Engine ist 100 Einheiten groß.
		const FVector Scale(0.01f, Length / 100.f, FMath::Max(Thick, 0.01f) / 100.f);
		const FQuat Rotation(FVector::XAxisVector, Angle);
		LayerTransforms[P.Group].Emplace(Rotation, Position + Offset, Scale);
	}

	for (int32 Layer = 0; Layer < NumLayers; ++Layer)
	{
		if (LayerTransforms[Layer].Num() > 0)
		{
			Layers[Layer]->BatchUpdateInstancesTransforms(0, LayerTransforms[Layer], false, true, true);
		}
	}
}

void AMEPFlowFieldActor::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	MEP::GetSceneSize(GetWorld(), Width, Height);
	EnsureParticleCount();

	const bool bMoving = IsAnimating();
	if (bMoving)
	{
		// dt auf 60 fps normiert und begrenzt, damit Ruckler keine Sprünge erzeugen.
		Step(FMath::Min(DeltaSeconds * 60.f, 3.f));
	}
	UpdateInstances(bMoving);
}
