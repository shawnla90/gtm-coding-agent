# <Name> — Clearbox offer pack

Generated: <YYYY-MM-DD>
Inputs: domain `<domain>` · brief supplied: yes/no · codebase read: yes/no · own-words: yes/no

## Paste into clearbox.to

Plain text, field by field. No markdown emphasis anywhere in these blocks.

**Name**

```
<Name>
```

**One-liner** (<N>/80 chars)

```
<X is a [category] for [who]>
```

**Selling points**

```
- <slot-shaped point 1>
- <slot-shaped point 2>
- <slot-shaped point 3>
- <slot-shaped point 4>
- <slot-shaped point 5>
```

## Beyond the form

These fields exist in the Convex offers document behind the form. Some the form asks for (competitors, rooms to watch); the rest are ready for when submission gets wired.

**Keywords** (~10, lowercase, buyer language)

```
<keyword 1>, <keyword 2>, ...
```

**Competitor brands** (lowercase tokens)

```
<brand 1>, <brand 2>, ...
```

**Own brands**

```
<Name>[, <parent brand>]
```

**Tracked subreddits** (5, all verified to exist)

```
<sub 1>, <sub 2>, <sub 3>, <sub 4>, <sub 5>
```

Swap candidates: `<sub 6>, <sub 7>, <sub 8>, <sub 9>, <sub 10>`

## Reference JSON

```json
{
  "_comment": "REFERENCE ONLY - field names match the Convex offers document. Clearbox has no local provisioning: accounts are self-serve on Convex and nothing local writes to it. The user pastes the blocks above into the form at clearbox.to.",
  "name": "<Name>",
  "description": "<Name> - <tag>\n\nOne-liner: <one-liner>\n\nSelling points:\n- <point 1>\n- <point 2>\n- <point 3>",
  "keywords": ["<keyword 1>", "<keyword 2>"],
  "competitorBrands": ["<brand 1>", "<brand 2>"],
  "ownBrands": ["<Name>"],
  "trackedSubreddits": ["<sub 1>", "<sub 2>", "<sub 3>", "<sub 4>", "<sub 5>"],
  "domains": ["<domain>"],
  "_swap_candidates": ["<sub 6>", "<sub 7>", "<sub 8>", "<sub 9>", "<sub 10>"]
}
```

## Sources

One line per selling point, keyed by number. Keywords/competitors/subs get a line each where the source is not obvious from the point sources.

1. <URL — what it backs>
2. <URL — what it backs>
