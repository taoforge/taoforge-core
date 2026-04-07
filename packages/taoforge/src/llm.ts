import { TaoForgeConfig } from "./types.js";

export interface LLMResponse {
  text: string;
  tokens?: number;
}

export async function generate(
  prompt: string,
  systemPrompt: string,
  config: TaoForgeConfig & { temperature?: number },
): Promise<LLMResponse> {
  if (config.provider === "anthropic") {
    return generateAnthropic(prompt, systemPrompt, config);
  }
  return generateOpenAI(prompt, systemPrompt, config);
}

async function generateOpenAI(
  prompt: string,
  systemPrompt: string,
  config: TaoForgeConfig & { temperature?: number },
): Promise<LLMResponse> {
  const { default: OpenAI } = await import("openai");
  const client = new OpenAI({ apiKey: config.apiKey });
  const res = await client.chat.completions.create({
    model: config.model,
    temperature: config.temperature ?? 0.7,
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: prompt },
    ],
    max_tokens: 512,
  });
  return {
    text: res.choices[0]?.message?.content ?? "",
    tokens: res.usage?.total_tokens,
  };
}

async function generateAnthropic(
  prompt: string,
  systemPrompt: string,
  config: TaoForgeConfig & { temperature?: number },
): Promise<LLMResponse> {
  const Anthropic = await import("@anthropic-ai/sdk");
  const client = new Anthropic.default({ apiKey: config.apiKey });
  const res = await client.messages.create({
    model: config.model,
    max_tokens: 512,
    temperature: config.temperature ?? 0.7,
    system: systemPrompt,
    messages: [{ role: "user", content: prompt }],
  });
  const block = res.content[0];
  return {
    text: block.type === "text" ? block.text : "",
    tokens: res.usage?.input_tokens + res.usage?.output_tokens,
  };
}
