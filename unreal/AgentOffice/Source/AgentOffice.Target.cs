using UnrealBuildTool;
using System.Collections.Generic;

public class AgentOfficeTarget : TargetRules
{
	public AgentOfficeTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("AgentOffice");
	}
}
