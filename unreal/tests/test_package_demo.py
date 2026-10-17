"""Static checks for Scripts/package_demo.ps1.

CI does not install Unreal Engine. These tests read the script and confirm
the RunUAT BuildCookRun arguments. They do not cook, zip, or launch the editor.
"""

import re
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "Scripts"
sys.path.insert(0, str(SCRIPTS))

import garden_logic

SCRIPT = SCRIPTS / "package_demo.ps1"
README = Path(__file__).resolve().parents[1] / "README.md"

UAT_ARGS = [
    "'BuildCookRun'",
    '"-project=$ProjectPath"',
    "'-noP4'",
    "'-platform=Win64'",
    '"-clientconfig=$ClientConfig"',
    "'-build'",
    "'-cook'",
    "'-stage'",
    "'-pak'",
    "'-archive'",
    '"-archivedirectory=$ArchiveDirectory"',
    '"-map=$joinedMaps"',
    "'-prereqs'",
    "'-compressed'",
    "'-unattended'",
    "'-utf8output'",
]


def load_script():
    return SCRIPT.read_text(encoding="utf-8")


def param_block(text):
    match = re.search(r"(?m)^param\s*\(\r?\n(.*?)^\)", text, re.S)
    if not match:
        raise AssertionError("param() block not found")
    return match.group(1)


def uat_block(text):
    match = re.search(r"# BEGIN UAT ARGS\r?\n(.*?)# END UAT ARGS", text, re.S)
    if not match:
        raise AssertionError("UAT argument block not found")
    return match.group(1)


def quoted_args(block):
    found = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("return"):
            continue
        if stripped[0] not in "'\"":
            continue
        if stripped.endswith(","):
            stripped = stripped[:-1].rstrip()
        found.append(stripped)
    return found


class PackageDemoTests(unittest.TestCase):
    def test_parameter_defaults(self):
        block = param_block(load_script())
        self.assertRegex(
            block,
            r"\[string\]\$EngineRoot\s*=\s*'C:\\Program Files\\Epic Games\\UE_5\.8'",
        )
        self.assertRegex(
            block,
            r"\[string\]\$Project\s*=\s*'C:\\ElyonSlice\\ElyonUE\.uproject'",
        )
        sets = re.findall(r"ValidateSet\(([^)]*)\)", block)
        self.assertEqual(len(sets), 1)
        self.assertEqual(re.findall(r"'([^']+)'", sets[0]), ["Shipping", "Development"])
        self.assertRegex(block, r"\[string\]\$Configuration\s*=\s*'Shipping'")
        self.assertIn(garden_logic.MAP_PATH, block)
        self.assertRegex(block, r"\[string\]\$ArchiveRoot\s*=\s*'C:\\ElyonSlice\\Packaged'")
        self.assertIn("[switch]$DryRun", block)

    def test_uat_argument_list(self):
        text = load_script()
        self.assertEqual(quoted_args(uat_block(text)), UAT_ARGS)
        self.assertRegex(text, r"\$joinedMaps = @\(\$MapList\) -join '\+'")
        self.assertIn(
            "Join-PackagePath -Parent $EngineRoot -Child 'Engine\\Build\\BatchFiles\\RunUAT.bat'",
            text,
        )
        self.assertNotIn("-platform=Win32", uat_block(text))
        self.assertNotIn("-platform=Linux", uat_block(text))

    def test_argument_validation_rules(self):
        text = load_script()
        self.assertIn("Configuration must be Shipping or Development.", text)
        self.assertIn("At least one map is required.", text)
        self.assertIn(r"^/Game/[A-Za-z0-9_./-]+$", text)
        self.assertIn("Map path cannot contain '+'", text)
        self.assertIn('["&|<>^%()]', text)
        self.assertIn("Project must be a .uproject path.", text)

    def test_zip_and_log(self):
        text = load_script()
        self.assertIn("'ElyonUE-Win64-{0}.zip'", text)
        self.assertIn("'package_demo-{0}.log'", text)
        self.assertIn("Compress-Archive -Path $PlatformDir -DestinationPath $DestinationZip", text)
        self.assertIn("tar.exe -a -cf $DestinationZip", text)
        for folder in ("Windows", "WindowsNoEditor", "WindowsClient"):
            self.assertIn("'%s'" % folder, text)
        self.assertIn("GetFileNameWithoutExtension($ProjectPath)", text)
        self.assertIn("UAT_ARGV=", text)
        self.assertIn("Add-Content -LiteralPath $script:DemoLogPath", text)

    def test_dry_run_does_not_launch_uat(self):
        text = load_script()
        self.assertIn("-SkipLaunch:$DryRun", text)
        dry = text.index("if ($SkipLaunch)")
        launch = text.index("FileName = 'cmd.exe'")
        self.assertLess(dry, launch)
        self.assertIn("Dry run: RunUAT was not started.", text)
        self.assertIn("No build was cooked and no zip was written.", text)

    def test_docs_name_the_same_paths(self):
        docs = README.read_text(encoding="utf-8")
        self.assertIn("Scripts/package_demo.ps1", docs)
        self.assertIn(r"C:\Program Files\Epic Games\UE_5.8", docs)
        self.assertIn(r"C:\ElyonSlice\ElyonUE.uproject", docs)
        self.assertIn(garden_logic.MAP_PATH, docs)
        self.assertIn("Shipping", docs)
        self.assertIn("Development", docs)
        self.assertIn("Win64", docs)
        self.assertIn("ElyonUE-Win64-Shipping.zip", docs)
        self.assertIn("package_demo-Shipping.log", docs)
        self.assertIn("-DryRun", docs)


if __name__ == "__main__":
    unittest.main()
