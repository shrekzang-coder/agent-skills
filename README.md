# agent-skills

A collection of [AgentSkills](https://github.com/anthropics/anthropic-cookbook/tree/main/skills) authored by [@shrekzang-coder](https://github.com/shrekzang-coder) for agent runtimes like OpenClaw, Claude Code, and Codex.

## Skills in this repo

| Skill | What it does |
|-------|--------------|
| [`xiaohongshu-publisher`](./xiaohongshu-publisher) | Publish image-text notes to Xiaohongshu (小红书) via a real logged-in browser, with human-like timing, DataTransfer file upload, React/Tiptap form filling, and real topic-tag autocomplete. |

## Using a skill

Each skill directory is self-contained. Drop it into your agent runtime's skills path (for OpenClaw this is typically `~/.openclaw/workspace/.agents/skills/<name>/` or `~/.agents/skills/<name>/`).

The runtime reads the YAML frontmatter in `SKILL.md` to decide when to trigger the skill. `scripts/` and `references/` are loaded on demand by the skill itself.

## Contributing

If you want to suggest edits, open an issue or a PR. These skills are written against live product UIs (Xiaohongshu, Gemini, etc.) and break when the vendor updates their frontend — heads-up reports of breakage are especially welcome.

## License

MIT — see [LICENSE](./LICENSE).
