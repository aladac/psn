---
description: 'Use when building TypeScript/Node.js command-line applications, creating CLI tools with Commander, or implementing terminal interfaces in TypeScript.'
---

# TypeScript CLI Development

Best practices for TypeScript/Node.js command-line applications.

## Framework: Commander.js

```typescript
// src/cli.ts
import { Command } from 'commander';
import { version } from '../package.json';

const program = new Command();

program
  .name('myapp')
  .description('Does useful things')
  .version(version, '-v, --version');

program
  .command('process <file>')
  .description('Process a file')
  .option('-o, --output <path>', 'Output file')
  .option('-V, --verbose', 'Verbose output')
  .action(async (file: string, options) => {
    if (options.verbose) {
      console.log(`Processing ${file}...`);
    }
    await processFile(file, options);
  });

program.parse();
```

## Required Flags

| Flag | Purpose |
|------|---------|
| `--version`, `-v` | Show package version |
| `--help`, `-h` | Show usage (Commander provides automatically) |

## Subcommands

```typescript
import { Command } from 'commander';
import { configCommands } from './commands/config';

const program = new Command();
program.name('myapp').version(version);
program.addCommand(configCommands());
program.parse();

// src/commands/config.ts
export function configCommands(): Command {
  const config = new Command('config').description('Manage configuration');

  config.command('show').description('Show current config').action(() => {
    const cfg = loadConfig();
    console.log(JSON.stringify(cfg, null, 2));
  });

  config.command('set <key> <value>').description('Set config value').action((key, value) => {
    setConfigValue(key, value);
  });

  return config;
}
```

## Output Patterns

### Colorized Output

```typescript
import chalk from 'chalk';

function success(message: string): void {
  console.log(chalk.green('✓'), message);
}

function error(message: string): void {
  console.error(chalk.red('✗'), message);
}

function warn(message: string): void {
  console.warn(chalk.yellow('⚠'), message);
}
```

### Tables

```typescript
import Table from 'cli-table3';

function listItems(items: Item[]): void {
  const table = new Table({
    head: ['ID', 'Name', 'Status'],
    style: { head: ['cyan'] },
  });
  for (const item of items) {
    table.push([item.id, item.name, item.status]);
  }
  console.log(table.toString());
}
```

### Progress Bars

```typescript
import cliProgress from 'cli-progress';

async function processFiles(files: string[]): Promise<void> {
  const bar = new cliProgress.SingleBar({
    format: 'Processing |{bar}| {percentage}% | {value}/{total}',
  });
  bar.start(files.length, 0);
  for (const file of files) {
    await processFile(file);
    bar.increment();
  }
  bar.stop();
}
```

### Spinners

```typescript
import ora from 'ora';

async function fetchData(): Promise<Data> {
  const spinner = ora('Fetching data...').start();
  try {
    const data = await api.fetch();
    spinner.succeed('Data fetched');
    return data;
  } catch (error) {
    spinner.fail('Failed to fetch data');
    throw error;
  }
}
```

## Configuration

### Config File (cosmiconfig)

```typescript
import { cosmiconfig } from 'cosmiconfig';

const explorer = cosmiconfig('myapp');

async function loadConfig(): Promise<Config> {
  const result = await explorer.search();
  return result?.config ?? {};
}
```

### Environment Variables

```typescript
import { z } from 'zod';

const envSchema = z.object({
  MYAPP_API_KEY: z.string(),
  MYAPP_DEBUG: z.coerce.boolean().default(false),
  MYAPP_TIMEOUT: z.coerce.number().default(30000),
});

const env = envSchema.parse(process.env);
```

## Error Handling

```typescript
program.command('process <file>').action(async (file: string) => {
  try {
    await processFile(file);
    success(`Processed ${file}`);
  } catch (err) {
    if (err instanceof FileNotFoundError) {
      error(`File not found: ${file}`);
      process.exit(1);
    }
    throw err;
  }
});

process.on('uncaughtException', (err) => {
  error(`Unexpected error: ${err.message}`);
  process.exit(1);
});

process.on('SIGINT', () => {
  warn('\nAborted');
  process.exit(130);
});
```

## Interactive Prompts

```typescript
import inquirer from 'inquirer';

async function setup(): Promise<void> {
  const answers = await inquirer.prompt([
    {
      type: 'password',
      name: 'apiKey',
      message: 'API Key:',
      validate: (input) => input.length > 0 || 'Required',
    },
    {
      type: 'list',
      name: 'env',
      message: 'Environment:',
      choices: ['development', 'staging', 'production'],
    },
    {
      type: 'confirm',
      name: 'save',
      message: 'Save configuration?',
      default: true,
    },
  ]);

  if (answers.save) {
    await saveConfig(answers);
    success('Configuration saved');
  }
}
```

## package.json Setup

```json
{
  "name": "myapp",
  "version": "1.0.0",
  "type": "module",
  "bin": { "myapp": "./dist/cli.js" },
  "scripts": {
    "build": "tsc",
    "start": "tsx src/cli.ts",
    "test": "vitest"
  },
  "dependencies": {
    "commander": "^12.0.0",
    "chalk": "^5.3.0",
    "cli-table3": "^0.6.0",
    "ora": "^8.0.0",
    "inquirer": "^9.0.0",
    "cosmiconfig": "^9.0.0"
  }
}
```

## Project Structure

```
myapp/
├── src/
│   ├── cli.ts              # Entry point
│   ├── commands/           # Command implementations
│   │   ├── config.ts
│   │   └── process.ts
│   ├── lib/                # Business logic
│   └── utils/
│       └── output.ts       # success/error/warn helpers
├── tests/
│   └── cli.test.ts
├── package.json
└── tsconfig.json
```

## Build for Distribution

Add shebang to entry point:

```typescript
#!/usr/bin/env node
// src/cli.ts
import { Command } from 'commander';
```

## Summary

| Component | Library |
|-----------|---------|
| CLI framework | `commander` |
| Colors | `chalk` |
| Prompts | `inquirer` |
| Progress | `cli-progress` |
| Spinners | `ora` |
| Tables | `cli-table3` |
| Config | `cosmiconfig` |
