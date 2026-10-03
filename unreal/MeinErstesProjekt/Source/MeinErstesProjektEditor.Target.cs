using UnrealBuildTool;
using System.Collections.Generic;

public class MeinErstesProjektEditorTarget : TargetRules
{
	public MeinErstesProjektEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("MeinErstesProjekt");
	}
}
