#!/usr/bin/env node
import { program } from "commander";
import chalk from "chalk";
import * as readline from "readline";
import { runEval } from "./eval.js";
import { submitResults } from "./submit.js";
import { CycleResult } from "./types.js";

// ── Wizard helpers ────────────────────────────────────────────────────────────

const NAMES = [
  "Archimedes", "Pythagoras", "Thales", "Eratosthenes", "Hipparchus",
  "Nearchus", "Pytheas", "Hanno", "Eudoxus", "Aristotle",
  "Hypatia", "Euclid", "Democritus", "Heraclitus", "Anaximander",
];

const PROVIDERS: { id: "openai" | "anthropic"; label: string; models: string[] }[] = [
  { id: "openai", label: "OpenAI", models: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"] },
  { id: "anthropic", label: "Anthropic", models: ["claude-haiku-4-5-20251001", "claude-sonnet-4-5-20251001", "claude-3-5-haiku-20241022"] },
];

function ask(rl: readline.Interface, prompt: string): Promise<string> {
  return new Promise(r => rl.question(prompt, r));
}

function askHidden(prompt: string): Promise<string> {
  return new Promise(resolve => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    process.stdout.write(prompt);
    const stdin = process.stdin;
    if (stdin.isTTY) stdin.setRawMode(true);
    let buf = "";
    const onData = (ch: Buffer) => {
      const c = ch.toString();
      if (c === "\n" || c === "\r") {
        if (stdin.isTTY) stdin.setRawMode(false);
        stdin.removeListener("data", onData);
        process.stdout.write("\n");
        rl.close();
        resolve(buf);
      } else if (c === "\x7f" || c === "\b") {
        if (buf.length > 0) {
          buf = buf.slice(0, -1);
          process.stdout.write("\b \b");
        }
      } else if (c === "\x03") {
        process.exit(0);
      } else {
        buf += c;
        process.stdout.write("*");
      }
    };
    stdin.resume();
    stdin.on("data", onData);
  });
}

async function wizard() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  console.log();
  console.log(chalk.bold("  \u03C4 TaoForge"));
  console.log(chalk.dim("  Self-improving agent experiment on Bittensor"));
  console.log();
  console.log(chalk.dim("  Let's set up your agent.\n"));

  // 1. Agent name
  const randomName = NAMES[Math.floor(Math.random() * NAMES.length)];
  const nameInput = await ask(rl, `  Agent name ${chalk.dim(`[${randomName}]`)}: `);
  const agentName = nameInput.trim() || randomName;
  console.log();

  // 2. Provider
  console.log("  Provider:");
  PROVIDERS.forEach((p, i) => {
    const rec = i === 0 ? chalk.dim(" (recommended)") : "";
    console.log(`    ${chalk.bold(`[${i + 1}]`)} ${p.label}${rec}`);
  });
  const provInput = await ask(rl, `  ${chalk.dim(">")} `);
  const provIdx = Math.max(0, Math.min(PROVIDERS.length - 1, parseInt(provInput || "1") - 1));
  const provider = PROVIDERS[provIdx];
  console.log();

  // 3. Model
  console.log("  Model:");
  provider.models.forEach((m, i) => {
    const rec = i === 0 ? chalk.dim(" (recommended)") : "";
    console.log(`    ${chalk.bold(`[${i + 1}]`)} ${m}${rec}`);
  });
  const modelInput = await ask(rl, `  ${chalk.dim(">")} `);
  const modelIdx = Math.max(0, Math.min(provider.models.length - 1, parseInt(modelInput || "1") - 1));
  const model = provider.models[modelIdx];
  console.log();

  // 4. API key (hidden input)
  rl.close();
  const apiKey = await askHidden(`  API key: `);
  if (!apiKey.trim()) {
    console.log(chalk.red("\n  Error: API key is required."));
    process.exit(1);
  }
  const masked = "*".repeat(Math.max(0, apiKey.length - 4)) + apiKey.slice(-4);
  console.log(chalk.dim(`  Key     ${masked}`));
  console.log();

  // 5. Cycles
  const rl2 = readline.createInterface({ input: process.stdin, output: process.stdout });
  const cyclesInput = await ask(rl2, `  Cycles ${chalk.dim("[10]")}: `);
  const cycles = parseInt(cyclesInput || "10") || 10;
  rl2.close();

  // 6. Confirm
  console.log();
  console.log(chalk.bold("  Ready to run:"));
  console.log(chalk.dim(`  Agent   `) + chalk.bold(agentName));
  console.log(chalk.dim(`  Model   `) + chalk.bold(model));
  console.log(chalk.dim(`  Subnet  `) + chalk.bold("SN1"));
  console.log(chalk.dim(`  Cycles  `) + chalk.bold(String(cycles)));
  console.log();

  const rl3 = readline.createInterface({ input: process.stdin, output: process.stdout });
  await ask(rl3, chalk.dim("  Press enter to start..."));
  rl3.close();
  console.log();

  // Run the experiment
  await runExperiment({
    agentName,
    model,
    apiKey: apiKey.trim(),
    provider: provider.id,
    cycles,
    netuid: 1,
    submit: true,
    apiUrl: "https://taoforge.tech",
  });
}

// ── Shared run logic ──────────────────────────────────────────────────────────

interface RunOpts {
  agentName: string;
  model: string;
  apiKey: string;
  provider: "openai" | "anthropic";
  cycles: number;
  netuid: number;
  submit: boolean;
  apiUrl: string;
}

async function runExperiment(opts: RunOpts) {
  const config = {
    agentName: opts.agentName,
    model: opts.model,
    apiKey: opts.apiKey,
    provider: opts.provider,
    cycles: opts.cycles,
    netuid: opts.netuid,
  };

  let bestScore = 0;
  const startTime = Date.now();

  const onCycle = (cycle: CycleResult, current: number, _total: number) => {
    const icon = cycle.accepted ? chalk.green("\u2713") : chalk.dim("\u00B7");
    const delta = cycle.raw_improvement > 0
      ? chalk.green(`+${(cycle.raw_improvement * 100).toFixed(2)}%`)
      : chalk.dim(`${(cycle.raw_improvement * 100).toFixed(2)}%`);
    const score = chalk.bold(cycle.delta_score.toFixed(4));
    const mut = chalk.dim(cycle.mutation_type.replace(/_/g, " "));
    console.log(`  ${icon} Cycle ${String(current).padStart(2)} \u2502 ${score} ${delta} \u2502 ${mut}`);
    if (cycle.accepted && cycle.delta_score > bestScore) bestScore = cycle.delta_score;
  };

  try {
    console.log(chalk.dim("  Running self-improvement loop...\n"));
    const result = await runEval(config, onCycle);
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    console.log();
    console.log(chalk.bold("  Results"));
    console.log(`  Score    ${chalk.dim(result.initial_score.toFixed(4))} \u2192 ${chalk.bold(result.final_score.toFixed(4))}`);
    const pct = (result.total_improvement * 100).toFixed(2);
    console.log(`  Delta    ${result.total_improvement > 0 ? chalk.green("+" + pct + "%") : chalk.dim(pct + "%")}`);
    console.log(`  Cycles   ${result.total_cycles} (${result.accepted} accepted)`);
    console.log(`  Time     ${elapsed}s`);
    console.log();

    if (opts.submit) {
      process.stdout.write(chalk.dim("  Submitting to TaoForge dashboard... "));
      const sub = await submitResults(result, opts.apiUrl);
      if (sub.ok) {
        console.log(chalk.green("done"));
        console.log();
        console.log(`  ${chalk.bold(opts.agentName)} is now on the leaderboard.`);
        console.log(`  ${chalk.dim("View at")} ${chalk.cyan("taoforge.tech/dashboard")}`);
      } else {
        console.log(chalk.yellow("failed"));
        console.log(chalk.dim(`  Error: ${sub.error}`));
        console.log(chalk.dim("  Your results ran successfully \u2014 try submitting again later."));
      }
    }
    console.log();
  } catch (err: any) {
    console.error(chalk.red("\n  Error: ") + err.message);
    process.exit(1);
  }
}

// ── CLI program ───────────────────────────────────────────────────────────────

program
  .name("taoforge")
  .description("Join the TaoForge self-improvement experiment")
  .version("0.2.0")
  .action(() => {
    // Default: launch interactive wizard
    wizard().catch((err) => {
      console.error(chalk.red("\n  Error: ") + err.message);
      process.exit(1);
    });
  });

program
  .command("join")
  .description("Run with flags (advanced / scripting mode)")
  .requiredOption("--name <name>", "Your agent's name (e.g. Archimedes)")
  .requiredOption("--key <key>", "Your API key (OpenAI or Anthropic)")
  .option("--model <model>", "Model to use", "gpt-4o-mini")
  .option("--provider <provider>", "LLM provider: openai or anthropic", "openai")
  .option("--cycles <n>", "Number of improvement cycles", "10")
  .option("--netuid <n>", "Subnet to analyze", "1")
  .option("--api-url <url>", "TaoForge API URL", "https://taoforge.tech")
  .option("--no-submit", "Run locally without submitting results")
  .action(async (opts) => {
    console.log();
    console.log(chalk.bold("  \u03C4 TaoForge"));
    console.log(chalk.dim("  Self-improving agent experiment on Bittensor\n"));

    console.log(chalk.dim(`  Agent   `) + chalk.bold(opts.name));
    console.log(chalk.dim(`  Model   `) + chalk.bold(opts.model));
    console.log(chalk.dim(`  Subnet  `) + chalk.bold(`SN${opts.netuid}`));
    console.log(chalk.dim(`  Cycles  `) + chalk.bold(opts.cycles));
    console.log();

    await runExperiment({
      agentName: opts.name,
      model: opts.model,
      apiKey: opts.key,
      provider: opts.provider as "openai" | "anthropic",
      cycles: parseInt(opts.cycles),
      netuid: parseInt(opts.netuid),
      submit: opts.submit !== false,
      apiUrl: opts.apiUrl,
    });
  });

program.parse();
