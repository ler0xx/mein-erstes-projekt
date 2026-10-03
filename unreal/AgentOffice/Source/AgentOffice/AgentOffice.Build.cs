using UnrealBuildTool;

public class AgentOffice : ModuleRules
{
	public AgentOffice(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"UMG"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"Json",
			"Slate",
			"SlateCore"
		});
	}
}
