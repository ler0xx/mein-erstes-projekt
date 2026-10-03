#include "MEPShapes.h"

#include "Components/StaticMeshComponent.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"

UStaticMeshComponent* MEP::AddShape(AActor* Owner, USceneComponent* Parent, UStaticMesh* Mesh,
	UMaterialInterface* Material, const FTransform& RelativeTransform)
{
	UStaticMeshComponent* Shape = NewObject<UStaticMeshComponent>(Owner);
	Shape->SetMobility(EComponentMobility::Movable);
	Shape->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Shape->SetGenerateOverlapEvents(false);
	Shape->SetCastShadow(false);
	Shape->SetStaticMesh(Mesh);
	Shape->SetupAttachment(Parent);
	Shape->SetRelativeTransform(RelativeTransform);
	Shape->RegisterComponent();
	if (Material)
	{
		Shape->SetMaterial(0, Material);
	}
	Owner->AddInstanceComponent(Shape);
	return Shape;
}
