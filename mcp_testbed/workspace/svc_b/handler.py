from __future__ import annotations

from dataclasses import dataclass

SERVICE_NAME = "svc_b"
DEFAULT_LIMIT = 8


@dataclass(frozen=True)
class HandlerReport:
    service: str
    truncated: bool
    message: str


def cap_message(message: str, limit: int = DEFAULT_LIMIT) -> str:
    text = message.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def handle_request(message: str, limit: int = DEFAULT_LIMIT) -> HandlerReport:
    text = message.strip()
    capped = cap_message(text, limit)
    return HandlerReport(service=SERVICE_NAME, truncated=capped != text, message=capped)


# planner-safe padding starts here.
# pad 01
# pad 02
# pad 03
# pad 04
# pad 05
# pad 06
# pad 07
# pad 08
# pad 09
# pad 10
# pad 11
# pad 12
# pad 13
# pad 14
# mutation_intent: Branch D implementation
# model_response: Executor(qwen/Qwen/Qwen2.5-Coder-7B-Instruct) response for prompt length=23: I'm sorry, but I don't have any specific information about "Branch D implementation." Could you please provide more context or details? Are you referring to a particular project, system, or technology? Without additional information, it's difficult for me to give you an accurate and helpful response. If you can clarify your question or provide more specifics, I'll do my best to assist you.
# mutation_intent: Branch D implementation
# model_response: Executor(qwen/Qwen/Qwen2.5-Coder-7B-Instruct) response for prompt length=23: I'm sorry, but I'm not sure what you mean by "Branch D implementation." Could you please provide more context or clarify your question? Are you referring to a specific project, technology, or concept that involves branch D? Without additional information, it's difficult for me to give you an accurate and helpful response. If you can provide more details, I'll be happy to assist you further.
# mutation_intent: Branch D implementation
# model_response: Executor(qwen/Qwen/Qwen2.5-Coder-7B-Instruct) response for prompt length=23: I'm sorry, but I don't have any specific information about "Branch D implementation". Could you please provide more context or details so I can assist you better? Are you referring to a particular project, system, or concept? Without additional information, it's difficult for me to give you a meaningful response.
# mutation_intent: Branch D implementation
# model_response: Executor(qwen/Qwen/Qwen2.5-Coder-7B-Instruct) response for prompt length=23: I'm sorry, but I'm not sure what you're asking for with "Branch D implementation." Could you please provide more context or details? Are you referring to a specific project, system, or technology that has branch D? Or are you asking about the general concept of implementing a branch in software development?
# 
# If you can give me more information, I'll be better able to assist you with your question.
# mutation_intent: Branch D implementation
# model_response: Executor(qwen/Qwen/Qwen2.5-Coder-7B-Instruct) response for prompt length=23: I'm sorry, but I need more context to understand what you're asking about "Branch D implementation." Could you please provide more details or specify the topic you're referring to? Are you talking about a software development branch, a specific project, or something else entirely? The more information you can give me, the better I'll be able to assist you with your question.
# mutation_intent: Branch D implementation
# model_response: Executor(qwen/Qwen/Qwen2.5-Coder-7B-Instruct) response for prompt length=23: I'm sorry, but I need more context to understand what you're asking about "Branch D implementation." Could you please provide more details or specify the area of interest? For example:
# 
# 1. Are you referring to a specific project, system, or technology?
# 2. Is it related to software development, infrastructure, or something else?
# 3. What is the purpose of Branch D in this context?
# 
# Once you provide more information, I'll be able to give you a more accurate and helpful response.
# mutation_intent: Branch D implementation
# model_response: Executor(qwen/Qwen/Qwen2.5-Coder-7B-Instruct) response for prompt length=23: I'm sorry, but I don't have any specific information about "Branch D implementation" as it's not a commonly used term or concept in my knowledge base. Could you please provide more context or details so I can assist you better? Are you referring to a particular project, system, or technology that has a branch named "D"? If so, could you specify which one?
# pad 15
# pad 16
# pad 17
# pad 18
# pad 19
# pad 20
# pad 21
# pad 22
# pad 23
# pad 24
# pad 25
# pad 26
# pad 27
# pad 28
# pad 29
# pad 30
# pad 31
# pad 32
# pad 33
# pad 34
# pad 35


def summarize(message: str) -> str:
    report = handle_request(message)
    state = "truncated" if report.truncated else "plain"
    return f"{report.service}:{state}:{report.message}"