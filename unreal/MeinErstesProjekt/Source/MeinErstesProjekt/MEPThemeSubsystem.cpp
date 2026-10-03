#include "MEPThemeSubsystem.h"

#include "MeinErstesProjekt.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "TimerManager.h"
#include "UObject/Package.h"

#if WITH_EDITORONLY_DATA
#include "Materials/MaterialExpressionVectorParameter.h"
#endif

#if PLATFORM_WINDOWS
#include "Windows/AllowWindowsPlatformTypes.h"
#include "Windows/WindowsHWrapper.h"

namespace MEPWindows
{
	// Entspricht prefers-color-scheme: Windows speichert den App-Modus in der Registry.
	static bool ReadDarkMode(bool& bOutDark)
	{
		DWORD Value = 1;
		DWORD Size = sizeof(Value);
		const LSTATUS Result = ::RegGetValueW(
			HKEY_CURRENT_USER,
			L"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
			L"AppsUseLightTheme",
			RRF_RT_REG_DWORD,
			nullptr,
			&Value,
			&Size);
		if (Result != ERROR_SUCCESS)
		{
			return false;
		}
		bOutDark = Value == 0;
		return true;
	}

	// Entspricht prefers-reduced-motion: „Animationen in Windows anzeigen“ ist aus.
	static bool ReadReducedMotion(bool& bOutReduced)
	{
		BOOL bAnimations = TRUE;
		if (!::SystemParametersInfoW(SPI_GETCLIENTAREAANIMATION, 0, &bAnimations, 0))
		{
			return false;
		}
		bOutReduced = !bAnimations;
		return true;
	}
}

#include "Windows/HideWindowsPlatformTypes.h"
#endif

const FName MEP::ColorParam(TEXT("Color"));

void MEP::GetSceneSize(const UWorld* World, float& OutWidth, float& OutHeight, FVector2D* OutViewportSize)
{
	FVector2D ViewportSize(1920.0, 1080.0);
	if (World)
	{
		if (UGameViewportClient* Viewport = World->GetGameViewport())
		{
			FVector2D Size;
			Viewport->GetViewportSize(Size);
			if (Size.X > 1.0 && Size.Y > 1.0)
			{
				ViewportSize = Size;
			}
		}
	}

	OutWidth = SceneWidth;
	OutHeight = SceneWidth * float(ViewportSize.Y / ViewportSize.X);
	if (OutViewportSize)
	{
		*OutViewportSize = ViewportSize;
	}
}

FVector MEP::ViewportToScene(const UWorld* World, const FVector2D& PixelPosition, float Depth)
{
	float Width, Height;
	FVector2D ViewportSize;
	GetSceneSize(World, Width, Height, &ViewportSize);
	const float X = float(PixelPosition.X / ViewportSize.X) * Width;
	const float Y = float(PixelPosition.Y / ViewportSize.Y) * Height;
	return FVector(Depth, X - Width * 0.5f, Height * 0.5f - Y);
}

static FLinearColor Hex(const TCHAR* InHex, float Alpha = 1.f)
{
	FLinearColor Color(FColor::FromHex(InHex));
	Color.A = Alpha;
	return Color;
}

FMEPPalette FMEPPalette::Make(bool bDark)
{
	FMEPPalette P;
	if (bDark)
	{
		P.Bg = Hex(TEXT("0b0b12"));
		P.BgGlow = Hex(TEXT("191632"));
		P.Fg = Hex(TEXT("f2f1f7"));
		P.Muted = Hex(TEXT("a3a2b8"));
		P.Accent[0] = Hex(TEXT("8f7bff"));
		P.Accent[1] = Hex(TEXT("ff6f9c"));
		P.Accent[2] = Hex(TEXT("3fe0c5"));
		P.Glass = Hex(TEXT("141420"), 0.45f);
		P.GlassBorder = Hex(TEXT("ffffff"), 0.08f);
		P.FlowerDim = 0.88f;
	}
	else
	{
		P.Bg = Hex(TEXT("f6f4ef"));
		P.BgGlow = Hex(TEXT("ffffff"));
		P.Fg = Hex(TEXT("16161d"));
		P.Muted = Hex(TEXT("5b5b6b"));
		P.Accent[0] = Hex(TEXT("6d4aff"));
		P.Accent[1] = Hex(TEXT("ff5c8a"));
		P.Accent[2] = Hex(TEXT("12b5a6"));
		P.Glass = Hex(TEXT("ffffff"), 0.55f);
		P.GlassBorder = Hex(TEXT("16161d"), 0.08f);
		P.FlowerDim = 1.f;
	}
	return P;
}

bool UMEPThemeSubsystem::DoesSupportWorldType(const EWorldType::Type WorldType) const
{
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE;
}

void UMEPThemeSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
	Super::OnWorldBeginPlay(InWorld);

	FString Scheme;
	if (FParse::Value(FCommandLine::Get(), TEXT("Farbschema="), Scheme))
	{
		bDarkForced = true;
		bDark = Scheme.Equals(TEXT("dunkel"), ESearchCase::IgnoreCase) || Scheme.Equals(TEXT("dark"), ESearchCase::IgnoreCase);
	}

	int32 Reduced = 0;
	if (FParse::Value(FCommandLine::Get(), TEXT("ReduzierteBewegung="), Reduced))
	{
		bReducedMotionForced = true;
		bReducedMotion = Reduced != 0;
	}

	PollSystemSettings();
	Palette = FMEPPalette::Make(bDark);

	// Wie die matchMedia-Listener der Website: Änderungen am System werden übernommen.
	InWorld.GetTimerManager().SetTimer(PollTimer, this, &UMEPThemeSubsystem::PollSystemSettings, 1.5f, true);
}

void UMEPThemeSubsystem::Deinitialize()
{
	if (UWorld* World = GetWorld())
	{
		World->GetTimerManager().ClearTimer(PollTimer);
	}
	OnThemeChanged.Clear();
	Super::Deinitialize();
}

void UMEPThemeSubsystem::PollSystemSettings()
{
	bool bNewDark = bDark;
	bool bNewReduced = bReducedMotion;

#if PLATFORM_WINDOWS
	if (!bDarkForced)
	{
		MEPWindows::ReadDarkMode(bNewDark);
	}
	if (!bReducedMotionForced)
	{
		MEPWindows::ReadReducedMotion(bNewReduced);
	}
#endif

	if (bNewDark != bDark || bNewReduced != bReducedMotion)
	{
		bDark = bNewDark;
		bReducedMotion = bNewReduced;
		Palette = FMEPPalette::Make(bDark);
		UE_LOG(LogMEP, Log, TEXT("Farbschema: %s, reduzierte Bewegung: %s"),
			bDark ? TEXT("dunkel") : TEXT("hell"), bReducedMotion ? TEXT("ja") : TEXT("nein"));
		OnThemeChanged.Broadcast();
	}
}

UMaterialInterface* UMEPThemeSubsystem::GetBaseMaterial()
{
	if (BaseMaterial)
	{
		return BaseMaterial;
	}

#if WITH_EDITORONLY_DATA
	// Ein unbeleuchtetes Material mit einem Farbparameter, komplett im Code aufgebaut.
	// Das geht nur, solange Editor-Daten vorhanden sind (Editor, PIE, -game mit Editor-Binaries).
	UPackage* Package = GetTransientPackage();
	UMaterial* Material = NewObject<UMaterial>(Package,
		MakeUniqueObjectName(Package, UMaterial::StaticClass(), TEXT("M_MEP_Einfarbig")), RF_Transient);
	Material->SetShadingModel(MSM_Unlit);
	Material->bUsedWithInstancedStaticMeshes = true;

	UMaterialExpressionVectorParameter* Color = NewObject<UMaterialExpressionVectorParameter>(Material);
	Color->ParameterName = MEP::ColorParam;
	Color->DefaultValue = FLinearColor::White;
	Material->GetExpressionCollection().AddExpression(Color);
	Material->GetEditorOnlyData()->EmissiveColor.Connect(0, Color);

	Material->PostEditChange();
	BaseMaterial = Material;
	bUnlit = true;
#else
	// In einem gepackten Spiel gibt es keinen Material-Compiler. Dann nehmen wir das
	// beleuchtete Grundformen-Material der Engine (hat ebenfalls einen Parameter „Color“);
	// der GameMode stellt dafür ein Licht auf.
	BaseMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	bUnlit = false;
#endif

	return BaseMaterial;
}

bool UMEPThemeSubsystem::HasUnlitMaterial()
{
	GetBaseMaterial();
	return bUnlit;
}

UMaterialInstanceDynamic* UMEPThemeSubsystem::MakeColorMaterial(UObject* Outer, const FLinearColor& Color)
{
	UMaterialInstanceDynamic* Instance = UMaterialInstanceDynamic::Create(GetBaseMaterial(), Outer);
	SetColor(Instance, Color);
	return Instance;
}

void UMEPThemeSubsystem::SetColor(UMaterialInstanceDynamic* Material, const FLinearColor& Color)
{
	if (Material)
	{
		Material->SetVectorParameterValue(MEP::ColorParam, FLinearColor(Color.R, Color.G, Color.B, 1.f));
	}
}
