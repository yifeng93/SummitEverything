#!/bin/sh
# D4: tamper with the committed icon in the QA checkout, confirm the real build
# path fails closed instead of producing an icon-less .app, then restore.
set -u
cd /Users/yifengstudio/.codex/worktrees/qa-appicon || exit 9
ICON=native/Resources/AppIcon.icns
LOG=.local/qa/appicon/tamper-D4.log
ART=.local/dev/qa-appicon/tamper
GOOD_SHA=$(shasum -a 256 "$ICON" | awk '{print $1}')

restore() {
    rm -f "$ICON.bak"
    git checkout -- "$ICON"
    echo "RESTORED sha=$(shasum -a 256 "$ICON" | awk '{print $1}')"
    echo "GIT_STATUS_AFTER=$(git status --porcelain | wc -l | tr -d ' ')"
}
trap restore EXIT

{
echo "good sha before tamper: $GOOD_SHA"

echo "########## SCENARIO 1: wrong header ##########"
printf 'not-an-icns-at-all' > "$ICON"
echo "tampered sha: $(shasum -a 256 "$ICON" | awk '{print $1}')"
rm -rf "$ART/s1"; mkdir -p "$ART/s1"
SUMMIT_ALLOW_DIRTY=1 scripts/release-macos.sh \
    "$PWD/$ART/s1/SummitEverything Internal.app" \
    "$PWD/$ART/s1/SummitEverything-Internal.dmg"
echo "SCENARIO1_RELEASE_EXIT=$?"
echo "app produced? $(test -e "$ART/s1/SummitEverything Internal.app" && echo YES || echo NO)"
echo "dmg produced? $(test -e "$ART/s1/SummitEverything-Internal.dmg" && echo YES || echo NO)"

echo "########## SCENARIO 2: correct magic, truncated to 4 bytes ##########"
printf 'icns' > "$ICON"
rm -rf "$ART/s2"; mkdir -p "$ART/s2"
SUMMIT_ALLOW_DIRTY=1 scripts/release-macos.sh \
    "$PWD/$ART/s2/SummitEverything Internal.app" \
    "$PWD/$ART/s2/SummitEverything-Internal.dmg"
echo "SCENARIO2_RELEASE_EXIT=$?"
echo "app produced? $(test -e "$ART/s2/SummitEverything Internal.app" && echo YES || echo NO)"

echo "########## SCENARIO 3: missing file ##########"
mv "$ICON" "$ICON.bak"
rm -rf "$ART/s3"; mkdir -p "$ART/s3"
SUMMIT_ALLOW_DIRTY=1 scripts/release-macos.sh \
    "$PWD/$ART/s3/SummitEverything Internal.app" \
    "$PWD/$ART/s3/SummitEverything-Internal.dmg"
echo "SCENARIO3_RELEASE_EXIT=$?"
echo "app produced? $(test -e "$ART/s3/SummitEverything Internal.app" && echo YES || echo NO)"
mv "$ICON.bak" "$ICON"

echo "########## DONE ##########"
} >> "$LOG" 2>&1

echo "TAMPER_SCRIPT_EXIT=0"
