# Xbox 360 Unlocked FPS — Modified XEXs

Modified Xbox 360 executables for RGH/JTAG consoles, grouped by game in GitHub Releases.

## Downloads

Open **Releases** and choose your game. Each game release provides its modified XEX variants as separate downloads, plus any required update-data files, instructions, and SHA-256 hashes.

Match the release's Title ID, Media ID, executable version, and title-update requirements to your game before replacing files.

| Game | Title ID | Media ID in the supplied examples |
| --- | --- | --- |
| Rainbow Six Vegas 2 | `55530807` | `1982EE1E` |
| Bully: Scholarship Edition | `5454081A` | `0867AD86` |
| DiRT 3, original release | `434D083D` | `75036F79` |

Other releases or updates may require different files.

## Extract an ISO to get the XEX

1. Back up your original game files and `default.xex`.
2. If your source is an ISO, use **ISO to XEX** to extract the **complete game folder**. Keep all game files and subfolders together.
3. Locate `default.xex` in the extracted folder.
4. Download the modified XEX matching that game's build and update state.
5. Follow the release instructions. You can launch a separately named XEX through Neighborhood or a console file manager. For normal dashboard scanning, preserve the original under a backup name and name the selected modified executable `default.xex`.
6. Keep required update assets in the location stated by that release. For the DiRT 3 game-folder candidates, the matching `patch.nfs` belongs beside the XEX.
7. Test the complete extracted game through Neighborhood or your usual launcher before converting it to GOD.

A loose XEX contains executable code; the complete extracted game folder supplies the rest of the game.

## Convert the modified game to GOD

### ISO2GOD Next: convert the extracted/XEX folder directly

**Complete extracted game folder with the modified `default.xex` → ISO2GOD Next's XEX-folder option → GOD**

1. Start with the complete extracted game folder that works on your console, including any required update assets.
2. Ensure the chosen modified executable is named `default.xex`.
3. In **ISO2GOD Next**, choose the **XEX-folder** input option and select that complete game folder.
4. Convert directly to GOD. No ISO rebuilding step is needed for this method.

### Older ISO2GOD versions: use a rebuilt ISO

**Complete modified game folder → rebuilt Xbox 360 ISO → ISO2GOD → GOD**

1. Start with the same complete, working modified game folder.
2. Use an Xbox 360 ISO rebuilding tool to create an ISO from that folder.
3. Open the rebuilt ISO in an older **ISO2GOD** version that requires ISO input and convert it to GOD.

For either method, transfer the generated GOD package and its matching data folder to the console, preserving their names and directory structure. Refresh the dashboard's game scan and test the converted installation.

## Variants and console testing

The collection includes examples with console-test results reported by the contributor. Each release should identify the game build, selected variant, and observed console behavior; measured FPS is stated only when measurements are available.

- **Unlocked** variants remove the documented frame-rate/presentation restriction and can introduce screen tearing.
- **V-sync** variants, where supplied and explained for that game, use synchronized presentation. Performance still depends on the scene and console workload.
- **Original/base-game** and **TU-merged** variants have different update requirements. Follow the individual release instructions.

Observed results apply to the tested build and setup.

## Patch provenance and file checks

Release notes credit the supplied game-specific guides and record exact edits and hashes. Long byte signatures are used to identify matching code. Instructions and offsets for one executable build must be checked again against another build.

The supplied RSV2, Bully, and DiRT 3 histories are retained as references. User-reported console observations and independently reproduced file comparisons are recorded separately.

XexTool source and documentation: https://github.com/Team-Resurgent/XexTool
