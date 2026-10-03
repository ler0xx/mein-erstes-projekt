#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "MEPThemeSubsystem.generated.h"

class UMaterialInterface;
class UMaterialInstanceDynamic;

namespace MEP
{
	// Breite der Szene in Welt-Einheiten. Die orthografische Kamera zeigt genau
	// diese Breite, eine Einheit entspricht also bei 1920 px Fensterbreite einem Pixel.
	constexpr float SceneWidth = 1920.f;

	// Name des Farbparameters im Laufzeit-Material.
	extern const FName ColorParam;

	// Liefert Breite/Höhe der Szene (Höhe folgt dem Seitenverhältnis des Viewports)
	// und optional die Viewport-Größe in Pixeln.
	void GetSceneSize(const UWorld* World, float& OutWidth, float& OutHeight, FVector2D* OutViewportSize = nullptr);

	// Rechnet eine Pixelposition im Viewport in eine Weltposition auf der Bildebene um.
	FVector ViewportToScene(const UWorld* World, const FVector2D& PixelPosition, float Depth);
}

// Die Farben aus style.css, einmal hell und einmal dunkel.
struct FMEPPalette
{
	FLinearColor Bg;
	FLinearColor BgGlow;
	FLinearColor Fg;
	FLinearColor Muted;
	FLinearColor Accent[3];
	FLinearColor Glass;
	FLinearColor GlassBorder;
	float FlowerDim = 1.f;

	static FMEPPalette Make(bool bDark);
};

DECLARE_MULTICAST_DELEGATE(FOnMEPThemeChanged);

/**
 * Hält das aktuelle Farbschema (hell/dunkel) und den Wunsch nach reduzierter Bewegung.
 * Beides wird wie auf der Website aus den Systemeinstellungen gelesen
 * (Windows: App-Modus und „Animationen in Windows anzeigen“) und regelmäßig nachgeprüft.
 * Per Kommandozeile lässt sich beides festlegen: -Farbschema=hell|dunkel, -ReduzierteBewegung=0|1.
 *
 * Außerdem baut das Subsystem das einzige Material des Projekts zur Laufzeit auf.
 */
UCLASS()
class UMEPThemeSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;
	virtual void Deinitialize() override;

	bool IsDark() const { return bDark; }
	bool IsReducedMotion() const { return bReducedMotion; }
	const FMEPPalette& GetPalette() const { return Palette; }

	// Wird ausgelöst, wenn sich Farbschema oder Bewegungs-Einstellung ändern.
	FOnMEPThemeChanged OnThemeChanged;

	// Erzeugt eine einfarbige, unbeleuchtete Material-Instanz.
	UMaterialInstanceDynamic* MakeColorMaterial(UObject* Outer, const FLinearColor& Color);
	static void SetColor(UMaterialInstanceDynamic* Material, const FLinearColor& Color);

	// Ob das Laufzeit-Material unbeleuchtet ist (nur mit Editor-Daten möglich).
	bool HasUnlitMaterial();

protected:
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

private:
	void PollSystemSettings();
	UMaterialInterface* GetBaseMaterial();

	UPROPERTY(Transient)
	TObjectPtr<UMaterialInterface> BaseMaterial;

	FMEPPalette Palette;
	bool bDark = false;
	bool bReducedMotion = false;
	bool bDarkForced = false;
	bool bReducedMotionForced = false;
	bool bUnlit = false;
	FTimerHandle PollTimer;
};
