# Start with your setup assistant

You do not need to understand the code or read the developer manual. Give a
local coding agent this message:

> Set up https://github.com/m-amir-gomaa/DeepTutor, branch
> study-standardization, for me. Clone the public fork if necessary, then read
> AGENTS.md, study/SETUP-AGENT.md and study/platforms/README.md. Do the technical
> work yourself and guide me through one necessary human action at a time.
> I have one Codex account and no Modal account. Keep cloud processing disabled.
> Detect my OS, chip, memory and existing tools; preserve existing installations.
> I am studying medicine and want a separate research vault. Ask only for missing
> goals, books, language and preferences. Finish with a simple launcher, a checked
> introductory lesson from my own book and an honest readiness record.

Change the last two sentences if your subjects differ. The same setup supports
other disciplines; accounts, books and preferences belong to each learner.

On an M3 MacBook, begin with the [official OpenAI desktop installation guide](https://developers.openai.com/codex/app/),
sign in to your own account, select Codex and choose a local project folder.
Then send the message above. The agent can clone a public repository without
you creating a GitHub account. If macOS asks for a system password, enter it in
the local macOS prompt. Never send it to the agent.

The agent prepares `~/DeepTutor/Start Study.command`. After setup, double-click
that file in Finder to start the app and open Study setup in your own browser.
You may add it to the Dock or ask the agent for a shortcut. The first model
authorization in DeepTutor may ask you to sign in again; it can use the same
account. A second account and Modal are optional additions.

If something fails, say “Read SETUP-STATUS.md and repair the failing step.”
That file records actual checks and the next action; you do not have to diagnose
Python, Node, authentication, model downloads or MCP yourself.
