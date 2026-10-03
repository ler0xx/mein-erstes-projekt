#include "OfficeDirector.h"

#include "AgentCharacter.h"
#include "AgentOffice.h"
#include "Components/SceneComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "OfficeLayout.h"
#include "OfficeStateSubsystem.h"

AOfficeDirector::AOfficeDirector()
{
	PrimaryActorTick.bCanEverTick = false;

	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("SceneRoot"));
	AgentClass = AAgentCharacter::StaticClass();
}

void AOfficeDirector::BeginPlay()
{
	Super::BeginPlay();

	ReloadLayout();

	UGameInstance* GameInstance = GetGameInstance();
	UOfficeStateSubsystem* State = GameInstance ? GameInstance->GetSubsystem<UOfficeStateSubsystem>() : nullptr;
	if (!State)
	{
		UE_LOG(LogAgentOffice, Error, TEXT("OfficeDirector: OfficeStateSubsystem nicht gefunden."));
		return;
	}

	StateSubsystem = State;
	State->OnWorkerArrived.AddDynamic(this, &AOfficeDirector::HandleWorkerArrived);
	State->OnWorkerLeft.AddDynamic(this, &AOfficeDirector::HandleWorkerLeft);
	State->OnWorkerChanged.AddDynamic(this, &AOfficeDirector::HandleWorkerChanged);

	// Wer schon da ist, bevor das Level gestartet ist
	for (const FOfficeWorker& Worker : State->GetWorkersRef())
	{
		SpawnAgent(Worker);
	}
}

void AOfficeDirector::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	if (UOfficeStateSubsystem* State = StateSubsystem.Get())
	{
		State->OnWorkerArrived.RemoveDynamic(this, &AOfficeDirector::HandleWorkerArrived);
		State->OnWorkerLeft.RemoveDynamic(this, &AOfficeDirector::HandleWorkerLeft);
		State->OnWorkerChanged.RemoveDynamic(this, &AOfficeDirector::HandleWorkerChanged);
	}
	StateSubsystem.Reset();

	for (const TPair<FString, TObjectPtr<AAgentCharacter>>& Pair : Agents)
	{
		if (IsValid(Pair.Value))
		{
			Pair.Value->Destroy();
		}
	}
	Agents.Reset();

	Super::EndPlay(EndPlayReason);
}

void AOfficeDirector::ReloadLayout()
{
	Spots.Reset();
	SpotIndexById.Reset();
	UOfficeLayoutLibrary::LoadDeskLayout(LayoutFile, Spots);

	for (int32 Index = 0; Index < Spots.Num(); ++Index)
	{
		SpotIndexById.Add(Spots[Index].DeskId, Index);
	}

	// Bereits vorhandene Figuren an die (evtl. neuen) Plätze stellen
	for (const TPair<FString, TObjectPtr<AAgentCharacter>>& Pair : Agents)
	{
		if (IsValid(Pair.Value))
		{
			PlaceAgent(Pair.Value, Pair.Value->GetWorker());
		}
	}
}

AAgentCharacter* AOfficeDirector::FindAgent(const FString& WorkerId) const
{
	const TObjectPtr<AAgentCharacter>* Found = Agents.Find(WorkerId);
	return Found ? Found->Get() : nullptr;
}

bool AOfficeDirector::GetSpotWorldTransform(const FString& DeskId, FTransform& OutTransform) const
{
	if (const int32* Index = SpotIndexById.Find(DeskId))
	{
		OutTransform = Spots[*Index].ToLocalTransform() * GetActorTransform();
		return true;
	}
	return false;
}

void AOfficeDirector::HandleWorkerArrived(const FOfficeWorker& Worker)
{
	SpawnAgent(Worker);
}

void AOfficeDirector::HandleWorkerLeft(const FOfficeWorker& Worker)
{
	TObjectPtr<AAgentCharacter> Agent;
	if (Agents.RemoveAndCopyValue(Worker.Id, Agent) && IsValid(Agent))
	{
		Agent->Destroy();
		UE_LOG(LogAgentOffice, Log, TEXT("Figur entfernt: %s"), *Worker.Name);
	}
}

void AOfficeDirector::HandleWorkerChanged(const FOfficeWorker& Worker, const FOfficeWorker& Previous)
{
	AAgentCharacter* Agent = FindAgent(Worker.Id);
	if (!Agent)
	{
		SpawnAgent(Worker);
		return;
	}

	if (Worker.DeskId != Previous.DeskId)
	{
		PlaceAgent(Agent, Worker);
	}
	Agent->ApplyWorker(Worker);
}

void AOfficeDirector::SpawnAgent(const FOfficeWorker& Worker)
{
	UWorld* World = GetWorld();
	if (!World || Agents.Contains(Worker.Id))
	{
		return;
	}

	UClass* Class = AgentClass ? AgentClass.Get() : AAgentCharacter::StaticClass();

	FString SpotType;
	const FTransform SpawnTransform = ComputeAgentTransform(Worker, nullptr, SpotType);

	AAgentCharacter* Agent = World->SpawnActorDeferred<AAgentCharacter>(
		Class, SpawnTransform, this, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
	if (!Agent)
	{
		UE_LOG(LogAgentOffice, Error, TEXT("Figur für %s konnte nicht gespawnt werden."), *Worker.Name);
		return;
	}

	Agent->SetSpotType(SpotType);
	Agent->ApplyWorker(Worker);
	Agent->FinishSpawning(SpawnTransform);

	if (!AgentMeshOverride.IsNull())
	{
		Agent->SetBodyMesh(AgentMeshOverride.LoadSynchronous());
	}

	Agents.Add(Worker.Id, Agent);

	const FVector Location = SpawnTransform.GetLocation();
	UE_LOG(LogAgentOffice, Log, TEXT("Figur gespawnt: %s an %s (%s) bei X=%.0f Y=%.0f"),
		*Worker.Name, *Worker.DeskId, *SpotType, Location.X, Location.Y);
}

void AOfficeDirector::PlaceAgent(AAgentCharacter* Agent, const FOfficeWorker& Worker)
{
	FString SpotType;
	const FTransform Transform = ComputeAgentTransform(Worker, Agent, SpotType);
	Agent->SetActorTransform(Transform);
	Agent->SetSpotType(SpotType);
}

FTransform AOfficeDirector::ComputeAgentTransform(const FOfficeWorker& Worker, const AAgentCharacter* Self, FString& OutSpotType) const
{
	if (const int32* Index = SpotIndexById.Find(Worker.DeskId))
	{
		const FOfficeDeskSpot& Spot = Spots[*Index];

		// Teilen sich mehrere einen Platz, stellen sich weitere daneben
		int32 Others = 0;
		for (const TPair<FString, TObjectPtr<AAgentCharacter>>& Pair : Agents)
		{
			if (Pair.Value && Pair.Value != Self && Pair.Value->GetWorker().DeskId == Worker.DeskId)
			{
				++Others;
			}
		}

		FTransform Local = Spot.ToLocalTransform();
		Local.AddToTranslation(Local.GetRotation().RotateVector(FVector(0.f, SharedSpotSpacing * Others, 0.f)));
		OutSpotType = Spot.Type;
		return Local * GetActorTransform();
	}

	if (!WarnedUnknownDesks.Contains(Worker.DeskId))
	{
		UE_LOG(LogAgentOffice, Warning, TEXT("Platz '%s' (von %s) steht nicht im Grundriss – Figur wartet in der Lobby."), *Worker.DeskId, *Worker.Name);
		WarnedUnknownDesks.Add(Worker.DeskId);
	}

	int32 LobbyIndex = 0;
	for (const TPair<FString, TObjectPtr<AAgentCharacter>>& Pair : Agents)
	{
		if (Pair.Value && Pair.Value != Self && !SpotIndexById.Contains(Pair.Value->GetWorker().DeskId))
		{
			++LobbyIndex;
		}
	}

	OutSpotType = TEXT("lobby");
	const FTransform Local(FRotator(0.f, LobbyYaw, 0.f), LobbyLocation + FVector(-LobbySpacing * LobbyIndex, 0.f, 0.f));
	return Local * GetActorTransform();
}
