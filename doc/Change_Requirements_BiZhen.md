# BiZhen System Change Requirements Specification (Phase 2)

**Version:** 2.0
**Date:** 2026-01-31
**Status:** Approved for Implementation

## 1. Overview
This document outlines the functional and non-functional requirements for the "BiZhen" (笔阵) system's Phase 2 enhancements. The goal is to improve user control, data persistence, and process transparency, transforming the prototype into a robust productivity tool.

## 2. Functional Requirements (FR)

### FR-01: Document Export & Download
**Description:** Users must be able to download generated essays in standard document formats for local storage and editing.
**Specifications:**
- Support downloading individual essays.
- Supported formats: **.docx** (Word) and **.pdf** (Portable Document Format).
- The exported document should include:
    - Title
    - Essay Content
    - Generation Metadata (Style, Score, Time)

### FR-02: Session Persistence & Lifecycle Management
**Description:** The system must preserve generation history during an active session to prevent data loss on page refreshes, while ensuring privacy upon logout.
**Specifications:**
- **Auto-Save:** Generated essays and progress state must be persisted (e.g., via `localStorage` or Backend Session DB) so that refreshing the browser does not clear the current workspace.
- **Multi-Round History:** The system should track a history of generation tasks within the current login session.
- **Logout Protection:**
    - Upon clicking "Logout", a modal must appear warning: *"Logging out will destroy all generated content. Please verify you have saved necessary documents."*
    - Upon confirmation, the backend must purge legitimate session data associated with that user's temporary workspace.

### FR-03: Process Transparency (Intermediate Outputs)
**Description:** Users should be able to inspect the "thought process" of the Multi-Agent system by viewing the outputs of intermediate steps.
**Specifications:**
- The progress bar icons (Strategist, Librarian, Outliner) must be interactive (clickable).
- Clicking a completed node opens a modal displaying its specific output:
    - **Strategist**: The analysis of the prompt, central thesis, and style guidance.
    - **Librarian**: The search terms used and key reference materials found.
    - **Outliner**: The structural outline generated before writing.

### FR-04: Advanced Structural Constraints (Custom Prompts)
**Description:** Users require fine-grained control over the essay structure via a custom prompt interface.
**Specifications:**
- **Input Interface:** A "Structure constraints" text area in the generation form.
- **Scope Selection:** Users can apply these constraints to "All Styles" or specific styles.
- **Backend Enforcement:** The backend Writers must inject these constraints into the generation context.
- **Default Template:** The system must provide a built-in "Advanced Structure Template" that users can click to pre-fill.
    - **Template Content:**
      > 标题使用对仗式，每半句4~6字；首段130~170字，需要联系作文题目给的材料，必须阐释清自己的观点，点题，包含关键字词；后续围绕总论点写三个分论点，每个分论点占一个自然段；每段开头必须提出分论点，并结合常用的议论方式进行阐释，例如举例论证；对于举例论证，可以使用“排例”，就是把三个与分论点相关的人物事迹等写成排比句，气势磅礴，也可以对一个典型事例进行详细阐释说明，结合其他的论证手法等。需保证每一个分论点的论述方法都不太一样。结尾段需要收束全文，可以引用名人名言，加入“时代青年”的视角，提出新做法，并点题。

### FR-05: Bug Fixes & Quality Assurance
**Description:** Address identified discrepancies and rendering issues in the current prototype.
**Specifications:**
- **Score Consistency:**
    - **Issue:** Observed mismatch where the UI badge showed "19" while the grader text stated "57".
    - **Requirement:** Implement robust regex parsing in the backend `Grader` to strictly extract the final score (e.g., matching `**总分**: (\d+)`). Ensure the structured data returned to the frontend matches the text explanation.
- **Universal Markdown Rendering:**
    - **Issue:** Grader comments currently display raw Markdown characters (e.g., `**`, `##`).
    - **Requirement:** Apply the `ReactMarkdown` renderer to **all** text output areas, including specific critique/comment sections.
- **Comment Integrity:**
    - **Issue:** Some grader comments appeared truncated or missing.
    - **Requirement:** Ensure the database schema (`Text` type) and API response payload can handle the full length of the grader's generation without truncation.

## 3. Non-Functional Requirements (NFR)

### NFR-01: Localization & Aesthetics
**Description:** The user interface must be polished for a native Chinese experience.
**Specifications:**
- **Language**: All UI text (buttons, labels, status messages, error logs) must be in **Simplified Chinese**.
- **Typography**: Optimize font readability for Chinese characters.
- **Visuals**: Ensure layout is clean, modern, and aligned with the "Academic/Premium" aesthetic defined in Phase 1.

## 4. Implementation Notes
- **Docs Generation**: Use python libraries like `python-docx` and `reportlab` (or similar) on the backend to generate files dynamically.
- **Persistence**: Given the "anonymous/temporary" nature of the current tasks, consider using browser `localStorage` for the heavy lifting of state restoration to avoid complex backend user session management complexities if not strictly necessary.
- **Prompt Injection**: Update the `Writer` agent prompts to explicitly prioritize the user's structural instructions over default style defaults where they conflict.
