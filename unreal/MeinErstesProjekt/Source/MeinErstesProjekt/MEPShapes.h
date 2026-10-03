#pragma once

#include "CoreMinimal.h"

class AActor;
class USceneComponent;
class UStaticMesh;
class UStaticMeshComponent;
class UMaterialInterface;

namespace MEP
{
	// Hängt zur Laufzeit eine Grundform (Würfel, Kugel, Zylinder …) an einen Actor.
	// Ohne Kollision und Schatten, beweglich, mit dem angegebenen Material.
	UStaticMeshComponent* AddShape(AActor* Owner, USceneComponent* Parent, UStaticMesh* Mesh,
		UMaterialInterface* Material, const FTransform& RelativeTransform);
}
