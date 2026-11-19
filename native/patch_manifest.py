import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID)
prefix = "{" + ANDROID + "}"

path = Path(sys.argv[1])
tree = ET.parse(path)
manifest = tree.getroot()
application = manifest.find("application")

permission = ET.Element("uses-permission", {prefix + "name": "android.permission.INTERNET"})
manifest.insert(list(manifest).index(application), permission)

queries = ET.Element("queries")
intent = ET.SubElement(queries, "intent")
ET.SubElement(intent, "action", {prefix + "name": "android.intent.action.MAIN"})
ET.SubElement(intent, "category", {prefix + "name": "android.intent.category.LAUNCHER"})
manifest.insert(list(manifest).index(application), queries)
ET.SubElement(manifest, "uses-feature", {
    prefix + "name": "oculus.software.overlay_keyboard", prefix + "required": "false"
})

ET.SubElement(application, "meta-data", {
    prefix + "name": "com.oculus.supportedDevices",
    prefix + "value": "quest3|quest3s"
})
for activity in application.findall("activity"):
    if activity.get(prefix + "name") == "com.godot.game.GodotApp":
        activity.set(prefix + "screenOrientation", "unspecified")
        ET.SubElement(activity, "layout", {
            prefix + "defaultWidth": "1024dp", prefix + "defaultHeight": "680dp",
            prefix + "minWidth": "540dp", prefix + "minHeight": "360dp"
        })

for provider in application.findall("provider"):
    name = provider.get(prefix + "name")
    if name == "androidx.startup.InitializationProvider":
        provider.set(prefix + "authorities", "org.questpanel.macros.androidx-startup")

ET.SubElement(application, "meta-data", {
    prefix + "name": "org.godotengine.plugin.v2.QuestMacros",
    prefix + "value": "org.questpanel.macros.QuestMacrosPlugin"
})
service = ET.SubElement(application, "service", {
    prefix + "name": "org.questpanel.macros.MacroService",
    prefix + "label": "Keyquest",
    prefix + "permission": "android.permission.BIND_ACCESSIBILITY_SERVICE",
    prefix + "exported": "true"
})
intent_filter = ET.SubElement(service, "intent-filter")
ET.SubElement(intent_filter, "action", {
    prefix + "name": "android.accessibilityservice.AccessibilityService"
})
ET.SubElement(service, "meta-data", {
    prefix + "name": "android.accessibilityservice",
    prefix + "resource": "@xml/macro_accessibility"
})

ET.indent(tree)
tree.write(path, encoding="utf-8", xml_declaration=True)

# The Godot template stores a disabled themed icon as a Boolean in its
# mipmap resource slot. AAPT2 needs a reference when recompiling it.
mipmaps = path.parent / "res/values-anydpi-v26/mipmaps.xml"
if mipmaps.exists():
    mipmaps.write_text(mipmaps.read_text().replace(
        'name="themed_icon">false<', 'name="themed_icon">@mipmap/icon<'))
