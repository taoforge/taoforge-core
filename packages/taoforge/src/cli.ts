#!/usr/bin/env node
import { program } from "commander";
import chalk from "chalk";
import { runEval } from "./eval.js";
import { submitResults } from "./submit.js";
import { CycleResult } from "./types.js";

program
  .name("taoforge")
  .description("Join the TaoForge self-improvement experiment")
  .version("0.1.0");

program
  .command("join")
  .description("Run the self-improvement loop and submit your results")
  .requiredOption("--name <name>", "Your agent's name (e.g. Archimedes)")
  .requiredOption("--key <key>", "Your API key (OpenAI or Anthropic)")
  .option("--model <model>", "Model to use", "gpt-4o-mini")
  .option("--provider <provider>", "LLM provider: openai or anthropic", "openai")
  .option("--cycles <n>", "Number of improvement cycles", "10")
  .option("--netuid <n>", "Subnet to analyze", "1")
  .option("--api-url <url>", "TaoForge API URL", "https://spellingly-mealiest-ignacia.ngrok-free.app")
  .option("--no-submit", "Run locally without submitting results")
  .action(async (opts) => {
    console.log();
    console.log(chalk.bold("  τ TaoForge"));
    console.log(chalk.dim("  Self-improving agent experiment on Bittensor\n"));

    const provider = opts.provider as "openai" | "anthropic";

    console.log(chalk.dim(`  Agent   `) + chalk.bold(opts.name));
    console.log(chalk.dim(`  Model   `) + chalk.bold(opts.model));
    console.log(chalk.dim(`  Subnet  `) + chalk.bold(`SN${opts.netuid}`));
    console.log(chalk.dim(`  Cycles  `) + chalk.bold(opts.cycles));
    console.log();

    const config = {
      agentName: opts.name,
      model: opts.model,
      apiKey: opts.key,
      provider,
      cycles: parseInt(opts.cycles),
      netuid: parseInt(opts.netuid),
    };

    let bestScore = 0;
    const startTime = Date.now();

    const onCycle = (cycle: CycleResult, current: number, _total: number) => {
      const icon = cycle.accepted ? chalk.green("✓") : chalk.dim("·");
      const delta = cycle.raw_improvement > 0
        ? chalk.green(`+${(cycle.raw_improvement * 100).toFixed(2)}%`)
        : chalk.dim(`${(cycle.raw_improvement * 100).toFixed(2)}%`);
      const score = chalk.bold(cycle.delta_score.toFixed(4));
      const mut = chalk.dim(cycle.mutation_type.replace(/_/g, " "));
      console.log(`  ${icon} Cycle ${String(current).padStart(2)} │ ${score} ${delta} │ ${mut}`);
      if (cycle.accepted && cycle.delta_score > bestScore) bestScore = cycle.delta_score;
    };

    try {
      console.log(chalk.dim("  Running self-improvement loop...\n"));
      const result = await runEval(config, onCycle);
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

      console.log();
      console.log(chalk.bold("  Results"));
      console.log(`  Score    ${chalk.dim(result.initial_score.toFixed(4))} → ${chalk.bold(result.final_score.toFixed(4))}`);
      const pct = (result.total_improvement * 100).toFixed(2);
      console.log(`  Delta    ${result.total_improvement > 0 ? chalk.green("+" + pct + "%") : chalk.dim(pct + "%")}`);
      console.log(`  Cycles   ${result.total_cycles} (${result.accepted} accepted)`);
      console.log(`  Time     ${elapsed}s`);
      console.log();

      if (opts.submit !== false) {
        process.stdout.write(chalk.dim("  Submitting to TaoForge dashboard... "));
        const sub = await submitResults(result, opts.apiUrl);
        if (sub.ok) {
          console.log(chalk.green("done"));
          console.log();
          console.log(`  ${chalk.bold(opts.name)} is now on the leaderboard.`);
          console.log(`  ${chalk.dim("View at")} ${chalk.cyan("taoforge.tech/dashboard")}`);
        } else {
          console.log(chalk.yellow("failed"));
          console.log(chalk.dim(`  Error: ${sub.error}`));
          console.log(chalk.dim("  Your results ran successfully — try submitting again later."));
        }
      }
      console.log();
    } catch (err: any) {
      console.error(chalk.red("\n  Error: ") + err.message);
      process.exit(1);
    }
  });

program.parse();
