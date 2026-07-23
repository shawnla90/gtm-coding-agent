# Releasing

New chapters and starters ship as tagged GitHub Releases, so anyone watching or starring the repo gets notified. This is the honest native reach: GitHub does not expose stargazer emails, and issues do not notify stargazers, so Releases are how a new drop reaches the people who starred. The steps:

1. Update `CHANGELOG.md`: add a new version block at the top (newest first) describing what shipped.
2. Tag and push:
   ```bash
   git tag -a v0.3.0 -m "Clearbox Reddit agency pack: intelligence + unmasking"
   git push origin v0.3.0
   ```
3. Cut the release from the tag, using the changelog block as the notes:
   ```bash
   # notes = the top version block of CHANGELOG.md
   awk '/^## \[/{c++} c==1{print} c==2{exit}' CHANGELOG.md > /tmp/notes.md
   gh release create v0.3.0 --title "v0.3.0 - Reddit intelligence + unmasking" --notes-file /tmp/notes.md
   ```

The `.github/workflows/release-on-chapter.yml` workflow drafts a release automatically when `chapters/**` or `starters/**` change on `main`. A draft does not notify anyone until a human clicks publish, so you always get a review step.

Watchers who chose "Releases" get an email. Stargazers see the release in their GitHub home feed. To catch them yourself: **Watch, then Custom, then Releases**.

Versioning: MAJOR for a breaking restructure, MINOR for a new chapter or starter, PATCH for fixes.
