#### Context needed for flow.py
from pocketflow import Flow
# Import all node classes from nodes.py
from nodes import (
    FetchRepo,
    IdentifyAbstractions,
    AnalyzeRelationships,
    OrderChapters,
    WriteChapters,
    CombineTutorial
)

def create_tutorial_flow():
    """Creates and returns the codebase tutorial generation flow."""

    # Instantiate nodes
    fetch_repo = FetchRepo()
    identify_abstractions = IdentifyAbstractions(max_retries=5, wait=20)
    analyze_relationships = AnalyzeRelationships(max_retries=5, wait=20)
    order_chapters = OrderChapters(max_retries=5, wait=20)
    write_chapters = WriteChapters(max_retries=5, wait=20) # This is a BatchNode
    combine_tutorial = CombineTutorial()

    # Connect nodes in sequence based on the design
    fetch_repo >> identify_abstractions
    identify_abstractions >> analyze_relationships
    analyze_relationships >> order_chapters
    order_chapters >> write_chapters
    write_chapters >> combine_tutorial

    # Create the flow starting with FetchRepo
    tutorial_flow = Flow(start=fetch_repo)

    return tutorial_flow

######## Context needed for main.py
import dotenv
import os
import argparse
# Import the function that creates the flow
from flow import create_tutorial_flow

# dotenv.load_dotenv()  # disabled due to missing python-dotenv

# Default file patterns
DEFAULT_INCLUDE_PATTERNS = {
    "*.py", "*.js", "*.jsx", "*.ts", "*.tsx", "*.go", "*.java", "*.pyi", "*.pyx",
    "*.c", "*.cc", "*.cpp", "*.h", "*.md", "*.rst", "Dockerfile",
    "Makefile", "*.yaml", "*.yml",
}

DEFAULT_EXCLUDE_PATTERNS = {
    "venv/*", ".venv/*", "*test*", "tests/*", "docs/*", "examples/*", "v1/*",
    "dist/*", "build/*", "experimental/*", "deprecated/*",
    "legacy/*", ".git/*", ".github/*", ".next/*", ".vscode/*", "obj/*", "bin/*", "node_modules/*", "*.log"
}

# --- Main Function ---
def main():
    parser = argparse.ArgumentParser(description="Generate a tutorial for a GitHub codebase or local directory.")

    # Create mutually exclusive group for source
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--repo", help="URL of the public GitHub repository.")
    source_group.add_argument("--dir", help="Path to local directory.")

    parser.add_argument("-n", "--name", help="Project name (optional, derived from repo/directory if omitted).")
    parser.add_argument("-t", "--token", help="GitHub personal access token (optional, reads from GITHUB_TOKEN env var if not provided).")
    parser.add_argument("-o", "--output", default="output", help="Base directory for output (default: ./output).")
    parser.add_argument("-i", "--include", nargs="+", help="Include file patterns (e.g. '*.py' '*.js'). Defaults to common code files if not specified.")
    parser.add_argument("-e", "--exclude", nargs="+", help="Exclude file patterns (e.g. 'tests/*' 'docs/*'). Defaults to test/build directories if not specified.")
    parser.add_argument("-s", "--max-size", type=int, default=100000, help="Maximum file size in bytes (default: 100000, about 100KB).")
    # Add language parameter for multi-language support
    parser.add_argument("--language", default="english", help="Language for the generated tutorial (default: english)")

    args = parser.parse_args()

    # Get GitHub token from argument or environment variable if using repo
    github_token = None
    if args.repo:
        github_token = args.token or os.environ.get('GITHUB_TOKEN')
        if not github_token:
            print("Warning: No GitHub token provided. You might hit rate limits for public repositories.")

    # Initialize the shared dictionary with inputs
    shared = {
        "repo_url": args.repo,
        "local_dir": args.dir,
        "project_name": args.name, # Can be None, FetchRepo will derive it
        "github_token": github_token,
        "output_dir": args.output, # Base directory for CombineTutorial output

        # Add include/exclude patterns and max file size
        "include_patterns": set(args.include) if args.include else DEFAULT_INCLUDE_PATTERNS,
        "exclude_patterns": set(args.exclude) if args.exclude else DEFAULT_EXCLUDE_PATTERNS,
        "max_file_size": args.max_size,

        # Add language for multi-language support
        "language": args.language,

        # Outputs will be populated by the nodes
        "files": [],
        "abstractions": [],
        "relationships": {},
        "chapter_order": [],
        "chapters": [],
        "final_output_dir": None
    }

    # Display starting message with repository/directory and language
    print(f"Starting tutorial generation for: {args.repo or args.dir} in {args.language.capitalize()} language")

    # Create the flow instance
    tutorial_flow = create_tutorial_flow()

    # Run the flow
    tutorial_flow.run(shared)

if __name__ == "__main__":
    main()

######Context needed for nodes.py
import os
import yaml
from pocketflow import Node, BatchNode
from utils.crawl_github_files import crawl_github_files
from utils.call_llm import call_llm
from utils.crawl_local_files import crawl_local_files

# Helper to get content for specific file indices
def get_content_for_indices(files_data, indices):
    content_map = {}
    for i in indices:
        if 0 <= i < len(files_data):
            path, content = files_data[i]
            content_map[f"{i} # {path}"] = content # Use index + path as key for context
    return content_map

class FetchRepo(Node):
    def prep(self, shared):
        repo_url = shared.get("repo_url")
        local_dir = shared.get("local_dir")
        project_name = shared.get("project_name")

        if not project_name:
            # Basic name derivation from URL or directory
            if repo_url:
                project_name = repo_url.split('/')[-1].replace('.git', '')
            else:
                project_name = os.path.basename(os.path.abspath(local_dir))
            shared["project_name"] = project_name

        # Get file patterns directly from shared
        include_patterns = shared["include_patterns"]
        exclude_patterns = shared["exclude_patterns"]
        max_file_size = shared["max_file_size"]

        return {
            "repo_url": repo_url,
            "local_dir": local_dir,
            "token": shared.get("github_token"),
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "max_file_size": max_file_size,
            "use_relative_paths": True
        }

    def exec(self, prep_res):
        if prep_res["repo_url"]:
            print(f"Crawling repository: {prep_res['repo_url']}...")
            result = crawl_github_files(
                repo_url=prep_res["repo_url"],
                token=prep_res["token"],
                include_patterns=prep_res["include_patterns"],
                exclude_patterns=prep_res["exclude_patterns"],
                max_file_size=prep_res["max_file_size"],
                use_relative_paths=prep_res["use_relative_paths"]
            )
        else:
            print(f"Crawling directory: {prep_res['local_dir']}...")
            result = crawl_local_files(
                directory=prep_res["local_dir"],
                include_patterns=prep_res["include_patterns"],
                exclude_patterns=prep_res["exclude_patterns"],
                max_file_size=prep_res["max_file_size"],
                use_relative_paths=prep_res["use_relative_paths"]
            )

        # Convert dict to list of tuples: [(path, content), ...]
        files_list = list(result.get("files", {}).items())
        if len(files_list) == 0:
            raise(ValueError("Failed to fetch files"))
        print(f"Fetched {len(files_list)} files.")
        return files_list

    def post(self, shared, prep_res, exec_res):
        shared["files"] = exec_res # List of (path, content) tuples

class IdentifyAbstractions(Node):
    def prep(self, shared):
        files_data = shared["files"]
        project_name = shared["project_name"]  # Get project name
        language = shared.get("language", "english") # Get language

        # Helper to create context from files, respecting limits (basic example)
        def create_llm_context(files_data):
            context = ""
            file_info = [] # Store tuples of (index, path)
            for i, (path, content) in enumerate(files_data):
                entry = f"--- File Index {i}: {path} ---\n{content}\n\n"
                context += entry
                file_info.append((i, path))

            return context, file_info # file_info is list of (index, path)

        context, file_info = create_llm_context(files_data)
        # Format file info for the prompt (comment is just a hint for LLM)
        file_listing_for_prompt = "\n".join([f"- {idx} # {path}" for idx, path in file_info])
        return context, file_listing_for_prompt, len(files_data), project_name, language # Return language

    def exec(self, prep_res):
        context, file_listing_for_prompt, file_count, project_name, language = prep_res  # Unpack project name and language
        print(f"Identifying abstractions using LLM...")

        # Add language instruction and hints only if not English
        language_instruction = ""
        name_lang_hint = ""
        desc_lang_hint = ""
        if language.lower() != "english":
            language_instruction = f"IMPORTANT: Generate the `name` and `description` for each abstraction in **{language.capitalize()}** language. Do NOT use English for these fields.\n\n"
            # Keep specific hints here as name/description are primary targets
            name_lang_hint = f" (value in {language.capitalize()})"
            desc_lang_hint = f" (value in {language.capitalize()})"

        prompt = f"""
For the project `{project_name}`:

Codebase Context:
{context}

{language_instruction}Analyze the codebase context.
Identify the top 5-10 core most important abstractions to help those new to the codebase.

For each abstraction, provide:
1. A concise `name`{name_lang_hint}.
2. A beginner-friendly `description` explaining what it is with a simple analogy, in around 100 words{desc_lang_hint}.
3. A list of relevant `file_indices` (integers) using the format `idx # path/comment`.

List of file indices and paths present in the context:
{file_listing_for_prompt}

Format the output as a YAML list of dictionaries:

```yaml
- name: |
    Query Processing{name_lang_hint}
  description: |
    Explains what the abstraction does.
    It's like a central dispatcher routing requests.{desc_lang_hint}
  file_indices:
    - 0 # path/to/file1.py
    - 3 # path/to/related.py
- name: |
    Query Optimization{name_lang_hint}
  description: |
    Another core concept, similar to a blueprint for objects.{desc_lang_hint}
  file_indices:
    - 5 # path/to/another.js
# ... up to 10 abstractions
```"""
        response = call_llm(prompt)
        # DEBUG: log raw LLM response for abstractions
        print("DEBUG: Abstraction node raw LLM response:\n", response)

        # --- Validation ---
        if "```yaml" in response:
            yaml_str = response.strip().split("```yaml")[1].split("```")[0].strip()
        else:
            yaml_str = response.strip()
        print("DEBUG: Abstraction node extracted yaml_str:\n", yaml_str)
        abstractions = yaml.safe_load(yaml_str)

        if not isinstance(abstractions, list):
            raise ValueError("LLM Output is not a list")

        validated_abstractions = []
        for item in abstractions:
            if not isinstance(item, dict) or not all(k in item for k in ["name", "description", "file_indices"]):
                raise ValueError(f"Missing keys in abstraction item: {item}")
            if not isinstance(item["name"], str):
                 raise ValueError(f"Name is not a string in item: {item}")
            if not isinstance(item["description"], str):
                 raise ValueError(f"Description is not a string in item: {item}")
            if not isinstance(item["file_indices"], list):
                 raise ValueError(f"file_indices is not a list in item: {item}")

            # Validate indices
            validated_indices = []
            for idx_entry in item["file_indices"]:
                 try:
                     if isinstance(idx_entry, int):
                         idx = idx_entry
                     elif isinstance(idx_entry, str) and '#' in idx_entry:
                          idx = int(idx_entry.split('#')[0].strip())
                     else:
                          idx = int(str(idx_entry).strip())

                     if not (0 <= idx < file_count):
                         raise ValueError(f"Invalid file index {idx} found in item {item['name']}. Max index is {file_count - 1}.")
                     validated_indices.append(idx)
                 except (ValueError, TypeError):
                      raise ValueError(f"Could not parse index from entry: {idx_entry} in item {item['name']}")

            item["files"] = sorted(list(set(validated_indices)))
            # Store only the required fields
            validated_abstractions.append({
                "name": item["name"], # Potentially translated name
                "description": item["description"], # Potentially translated description
                "files": item["files"]
            })

        print(f"Identified {len(validated_abstractions)} abstractions.")
        return validated_abstractions

    def post(self, shared, prep_res, exec_res):
        shared["abstractions"] = exec_res # List of {"name": str, "description": str, "files": [int]}

class AnalyzeRelationships(Node):
    def prep(self, shared):
        abstractions = shared["abstractions"] # Now contains 'files' list of indices, name/description potentially translated
        files_data = shared["files"]
        project_name = shared["project_name"]  # Get project name
        language = shared.get("language", "english") # Get language

        # Create context with abstraction names, indices, descriptions, and relevant file snippets
        context = "Identified Abstractions:\n"
        all_relevant_indices = set()
        abstraction_info_for_prompt = []
        for i, abstr in enumerate(abstractions):
            # Use 'files' which contains indices directly
            file_indices_str = ", ".join(map(str, abstr['files']))
            # Abstraction name and description might be translated already
            info_line = f"- Index {i}: {abstr['name']} (Relevant file indices: [{file_indices_str}])\n  Description: {abstr['description']}"
            context += info_line + "\n"
            abstraction_info_for_prompt.append(f"{i} # {abstr['name']}") # Use potentially translated name here too
            all_relevant_indices.update(abstr['files'])

        context += "\nRelevant File Snippets (Referenced by Index and Path):\n"
        # Get content for relevant files using helper
        relevant_files_content_map = get_content_for_indices(
            files_data,
            sorted(list(all_relevant_indices))
        )
        # Format file content for context
        file_context_str = "\n\n".join(
            f"--- File: {idx_path} ---\n{content}"
            for idx_path, content in relevant_files_content_map.items()
        )
        context += file_context_str

        return context, "\n".join(abstraction_info_for_prompt), project_name, language # Return language

    def exec(self, prep_res):
        context, abstraction_listing, project_name, language = prep_res  # Unpack project name and language
        print(f"Analyzing relationships using LLM...")

        # Add language instruction and hints only if not English
        language_instruction = ""
        lang_hint = ""
        list_lang_note = ""
        if language.lower() != "english":
            language_instruction = f"IMPORTANT: Generate the `summary` and relationship `label` fields in **{language.capitalize()}** language. Do NOT use English for these fields.\n\n"
            lang_hint = f" (in {language.capitalize()})"
            list_lang_note = f" (Names might be in {language.capitalize()})" # Note for the input list

        prompt = f"""
Based on the following project abstractions and their relationships for the project ```` {project_name} ````:

List of Abstraction Indices and Names{list_lang_note}:
{abstraction_listing}

Context about relationships and project summary:
{context}

{language_instruction}Please provide:
1. A high-level `summary` of the project's main purpose and functionality in a few beginner-friendly sentences{lang_hint}. Use markdown formatting with **bold** and *italic* text to highlight important concepts.
2. A list (`relationships`) describing the key interactions between these abstractions. For each relationship, specify:
    - `from_abstraction`: Index of the source abstraction (e.g., `0 # AbstractionName1`)
    - `to_abstraction`: Index of the target abstraction (e.g., `1 # AbstractionName2`)
    - `label`: A brief label for the interaction **in just a few words**{lang_hint} (e.g., "Manages", "Inherits", "Uses").
    Ideally the relationship should be backed by one abstraction calling or passing parameters to another.
    Simplify the relationship and exclude those non-important ones.

IMPORTANT: Make sure EVERY abstraction is involved in at least ONE relationship (either as source or target). Each abstraction index must appear at least once across all relationships.

Format the output as YAML:

```yaml
summary: |
  A brief, simple explanation of the project{lang_hint}.
  Can span multiple lines with **bold** and *italic* for emphasis.
relationships:
  - from_abstraction: 0 # AbstractionName1
    to_abstraction: 1 # AbstractionName2
    label: "Manages"{lang_hint}
  - from_abstraction: 2 # AbstractionName3
    to_abstraction: 0 # AbstractionName1
    label: "Provides config"{lang_hint}
  # ... other relationships
```"""
        response = call_llm(prompt)
        # DEBUG: log raw LLM response for relationships analysis
        print("DEBUG: AnalyzeRelationships raw LLM response:\n", response)

        # --- Validation ---
        if "```yaml" in response:
            yaml_str = response.strip().split("```yaml")[1].split("```")[0].strip()
        else:
            yaml_str = response.strip()
        print("DEBUG: AnalyzeRelationships extracted yaml_str:\n", yaml_str)
        relationships_data = yaml.safe_load(yaml_str)

        if not isinstance(relationships_data, dict) or not all(k in relationships_data for k in ["summary", "relationships"]):
            raise ValueError("LLM output is not a dict or missing keys ('summary', 'relationships')")
        if not isinstance(relationships_data["summary"], str):
             raise ValueError("summary is not a string")
        if not isinstance(relationships_data["relationships"], list):
             raise ValueError("relationships is not a list")

        # Validate relationships structure
        validated_relationships = []
        num_abstractions = len(abstraction_listing.split('\n'))
        for rel in relationships_data["relationships"]:
             # Check for 'label' key
             if not isinstance(rel, dict) or not all(k in rel for k in ["from_abstraction", "to_abstraction", "label"]):
                  raise ValueError(f"Missing keys (expected from_abstraction, to_abstraction, label) in relationship item: {rel}")
             # Validate 'label' is a string
             if not isinstance(rel["label"], str):
                  raise ValueError(f"Relationship label is not a string: {rel}")

             # Validate indices
             try:
                 from_idx = int(str(rel["from_abstraction"]).split('#')[0].strip())
                 to_idx = int(str(rel["to_abstraction"]).split('#')[0].strip())
                 if not (0 <= from_idx < num_abstractions and 0 <= to_idx < num_abstractions):
                      raise ValueError(f"Invalid index in relationship: from={from_idx}, to={to_idx}. Max index is {num_abstractions-1}.")
                 validated_relationships.append({
                     "from": from_idx,
                     "to": to_idx,
                     "label": rel["label"] # Potentially translated label
                 })
             except (ValueError, TypeError):
                  raise ValueError(f"Could not parse indices from relationship: {rel}")

        print("Generated project summary and relationship details.")
        return {
            "summary": relationships_data["summary"], # Potentially translated summary
            "details": validated_relationships # Store validated, index-based relationships with potentially translated labels
        }


    def post(self, shared, prep_res, exec_res):
        # Structure is now {"summary": str, "details": [{"from": int, "to": int, "label": str}]}
        # Summary and label might be translated
        shared["relationships"] = exec_res

class OrderChapters(Node):
    def prep(self, shared):
        abstractions = shared["abstractions"] # Name/description might be translated
        relationships = shared["relationships"] # Summary/label might be translated
        project_name = shared["project_name"]  # Get project name
        language = shared.get("language", "english") # Get language

        # Prepare context for the LLM
        abstraction_info_for_prompt = []
        for i, a in enumerate(abstractions):
            abstraction_info_for_prompt.append(f"- {i} # {a['name']}") # Use potentially translated name
        abstraction_listing = "\n".join(abstraction_info_for_prompt)

        # Use potentially translated summary and labels
        summary_note = ""
        if language.lower() != "english":
             summary_note = f" (Note: Project Summary might be in {language.capitalize()})"

        context = f"Project Summary{summary_note}:\n{relationships['summary']}\n\n"
        context += "Relationships (Indices refer to abstractions above):\n"
        for rel in relationships['details']:
             from_name = abstractions[rel['from']]['name']
             to_name = abstractions[rel['to']]['name']
             # Use potentially translated 'label'
             context += f"- From {rel['from']} ({from_name}) to {rel['to']} ({to_name}): {rel['label']}\n" # Label might be translated

        list_lang_note = ""
        if language.lower() != "english":
             list_lang_note = f" (Names might be in {language.capitalize()})"

        return abstraction_listing, context, len(abstractions), project_name, list_lang_note

    def exec(self, prep_res):
        abstraction_listing, context, num_abstractions, project_name, list_lang_note = prep_res
        print("Determining chapter order using LLM...")
        # No language variation needed here in prompt instructions, just ordering based on structure
        # The input names might be translated, hence the note.
        prompt = f"""
Given the following project abstractions and their relationships for the project ```` {project_name} ````:

Abstractions (Index # Name){list_lang_note}:
{abstraction_listing}

Context about relationships and project summary:
{context}

If you are going to make a tutorial for ```` {project_name} ````, what is the best order to explain these abstractions, from first to last?
Ideally, first explain those that are the most important or foundational, perhaps user-facing concepts or entry points. Then move to more detailed, lower-level implementation details or supporting concepts.

Output the ordered list of abstraction indices, including the name in a comment for clarity. Use the format `idx # AbstractionName`.

```yaml
- 2 # FoundationalConcept
- 0 # CoreClassA
- 1 # CoreClassB (uses CoreClassA)
- ...
```

Now, provide the YAML output:
"""
        response = call_llm(prompt)

        # --- Validation ---
        if "```yaml" in response:
            yaml_str = response.strip().split("```yaml")[1].split("```")[0].strip()
        else:
            yaml_str = response.strip()
        print("DEBUG: OrderChapters extracted yaml_str:\n", yaml_str)
        ordered_indices_raw = yaml.safe_load(yaml_str)

        if not isinstance(ordered_indices_raw, list):
            raise ValueError("LLM output is not a list")

        ordered_indices = []
        seen_indices = set()
        for entry in ordered_indices_raw:
            try:
                 if isinstance(entry, int):
                     idx = entry
                 elif isinstance(entry, str) and '#' in entry:
                      idx = int(entry.split('#')[0].strip())
                 else:
                      idx = int(str(entry).strip())

                 if not (0 <= idx < num_abstractions):
                      raise ValueError(f"Invalid index {idx} in ordered list. Max index is {num_abstractions-1}.")
                 if idx in seen_indices:
                     raise ValueError(f"Duplicate index {idx} found in ordered list.")
                 ordered_indices.append(idx)
                 seen_indices.add(idx)

            except (ValueError, TypeError):
                 raise ValueError(f"Could not parse index from ordered list entry: {entry}")

        # Check if all abstractions are included
        if len(ordered_indices) != num_abstractions:
             raise ValueError(f"Ordered list length ({len(ordered_indices)}) does not match number of abstractions ({num_abstractions}). Missing indices: {set(range(num_abstractions)) - seen_indices}")

        print(f"Determined chapter order (indices): {ordered_indices}")
        return ordered_indices # Return the list of indices

    def post(self, shared, prep_res, exec_res):
        # exec_res is already the list of ordered indices
        shared["chapter_order"] = exec_res # List of indices

class WriteChapters(BatchNode):
    def prep(self, shared):
        chapter_order = shared["chapter_order"] # List of indices
        abstractions = shared["abstractions"]   # List of dicts, name/desc potentially translated
        files_data = shared["files"]
        language = shared.get("language", "english") # Get language

        # Get already written chapters to provide context
        # We store them temporarily during the batch run, not in shared memory yet
        # The 'previous_chapters_summary' will be built progressively in the exec context
        self.chapters_written_so_far = [] # Use instance variable for temporary storage across exec calls

        # Create a complete list of all chapters
        all_chapters = []
        chapter_filenames = {} # Store chapter filename mapping for linking
        for i, abstraction_index in enumerate(chapter_order):
            if 0 <= abstraction_index < len(abstractions):
                chapter_num = i + 1
                chapter_name = abstractions[abstraction_index]["name"] # Potentially translated name
                # Create safe filename (from potentially translated name)
                safe_name = "".join(c if c.isalnum() else '_' for c in chapter_name).lower()
                filename = f"{i+1:02d}_{safe_name}.md"
                # Format with link (using potentially translated name)
                all_chapters.append(f"{chapter_num}. [{chapter_name}]({filename})")
                # Store mapping of chapter index to filename for linking
                chapter_filenames[abstraction_index] = {"num": chapter_num, "name": chapter_name, "filename": filename}

        # Create a formatted string with all chapters
        full_chapter_listing = "\n".join(all_chapters)

        items_to_process = []
        for i, abstraction_index in enumerate(chapter_order):
            if 0 <= abstraction_index < len(abstractions):
                abstraction_details = abstractions[abstraction_index] # Contains potentially translated name/desc
                # Use 'files' (list of indices) directly
                related_file_indices = abstraction_details.get("files", [])
                # Get content using helper, passing indices
                related_files_content_map = get_content_for_indices(files_data, related_file_indices)

                # Get previous chapter info for transitions (uses potentially translated name)
                prev_chapter = None
                if i > 0:
                    prev_idx = chapter_order[i-1]
                    prev_chapter = chapter_filenames[prev_idx]

                # Get next chapter info for transitions (uses potentially translated name)
                next_chapter = None
                if i < len(chapter_order) - 1:
                    next_idx = chapter_order[i+1]
                    next_chapter = chapter_filenames[next_idx]

                items_to_process.append({
                    "chapter_num": i + 1,
                    "abstraction_index": abstraction_index,
                    "abstraction_details": abstraction_details, # Has potentially translated name/desc
                    "related_files_content_map": related_files_content_map,
                    "project_name": shared["project_name"],  # Add project name
                    "full_chapter_listing": full_chapter_listing,  # Add the full chapter listing (uses potentially translated names)
                    "chapter_filenames": chapter_filenames,  # Add chapter filenames mapping (uses potentially translated names)
                    "prev_chapter": prev_chapter,  # Add previous chapter info (uses potentially translated name)
                    "next_chapter": next_chapter,  # Add next chapter info (uses potentially translated name)
                    "language": language,  # Add language for multi-language support
                    # previous_chapters_summary will be added dynamically in exec
                })
            else:
                print(f"Warning: Invalid abstraction index {abstraction_index} in chapter_order. Skipping.")

        print(f"Preparing to write {len(items_to_process)} chapters...")
        return items_to_process # Iterable for BatchNode

    def exec(self, item):
        # This runs for each item prepared above
        abstraction_name = item["abstraction_details"]["name"] # Potentially translated name
        abstraction_description = item["abstraction_details"]["description"] # Potentially translated description
        chapter_num = item["chapter_num"]
        project_name = item.get("project_name")
        language = item.get("language", "english")
        print(f"Writing chapter {chapter_num} for: {abstraction_name} using LLM...")

        # Prepare file context string from the map
        file_context_str = "\n\n".join(
            f"--- File: {idx_path.split('# ')[1] if '# ' in idx_path else idx_path} ---\n{content}"
            for idx_path, content in item["related_files_content_map"].items()
        )

        # Get summary of chapters written *before* this one
        # Use the temporary instance variable
        previous_chapters_summary = "\n---\n".join(self.chapters_written_so_far)

        # Add language instruction and context notes only if not English
        language_instruction = ""
        concept_details_note = ""
        structure_note = ""
        prev_summary_note = ""
        instruction_lang_note = ""
        mermaid_lang_note = ""
        code_comment_note = ""
        link_lang_note = ""
        tone_note = ""
        if language.lower() != "english":
            lang_cap = language.capitalize()
            language_instruction = f"IMPORTANT: Write this ENTIRE tutorial chapter in **{lang_cap}**. Some input context (like concept name, description, chapter list, previous summary) might already be in {lang_cap}, but you MUST translate ALL other generated content including explanations, examples, technical terms, and potentially code comments into {lang_cap}. DO NOT use English anywhere except in code syntax, required proper nouns, or when specified. The entire output MUST be in {lang_cap}.\n\n"
            concept_details_note = f" (Note: Provided in {lang_cap})"
            structure_note = f" (Note: Chapter names might be in {lang_cap})"
            prev_summary_note = f" (Note: This summary might be in {lang_cap})"
            instruction_lang_note = f" (in {lang_cap})"
            mermaid_lang_note = f" (Use {lang_cap} for labels/text if appropriate)"
            code_comment_note = f" (Translate to {lang_cap} if possible, otherwise keep minimal English for clarity)"
            link_lang_note = f" (Use the {lang_cap} chapter title from the structure above)"
            tone_note = f" (appropriate for {lang_cap} readers)"

        prompt = f"""
{language_instruction}Write a very beginner-friendly tutorial chapter (in Markdown format) for the project `{project_name}` about the concept: "{abstraction_name}". This is Chapter {chapter_num}.

Concept Details{concept_details_note}:
- Name: {abstraction_name}
- Description:
{abstraction_description}

Complete Tutorial Structure{structure_note}:
{item["full_chapter_listing"]}

Context from previous chapters{prev_summary_note}:
{previous_chapters_summary if previous_chapters_summary else "This is the first chapter."}

Relevant Code Snippets (Code itself remains unchanged):
{file_context_str if file_context_str else "No specific code snippets provided for this abstraction."}

Instructions for the chapter (Generate content in {language.capitalize()} unless specified otherwise):
- Start with a clear heading (e.g., `# Chapter {chapter_num}: {abstraction_name}`). Use the provided concept name.

- If this is not the first chapter, begin with a brief transition from the previous chapter{instruction_lang_note}, referencing it with a proper Markdown link using its name{link_lang_note}.

- Begin with a high-level motivation explaining what problem this abstraction solves{instruction_lang_note}. Start with a central use case as a concrete example. The whole chapter should guide the reader to understand how to solve this use case. Make it very minimal and friendly to beginners.

- If the abstraction is complex, break it down into key concepts. Explain each concept one-by-one in a very beginner-friendly way{instruction_lang_note}.

- Explain how to use this abstraction to solve the use case{instruction_lang_note}. Give example inputs and outputs for code snippets (if the output isn't values, describe at a high level what will happen{instruction_lang_note}).

- Each code block should be BELOW 20 lines! If longer code blocks are needed, break them down into smaller pieces and walk through them one-by-one. Aggresively simplify the code to make it minimal. Use comments{code_comment_note} to skip non-important implementation details. Each code block should have a beginner friendly explanation right after it{instruction_lang_note}.

- Describe the internal implementation to help understand what's under the hood{instruction_lang_note}. First provide a non-code or code-light walkthrough on what happens step-by-step when the abstraction is called{instruction_lang_note}. It's recommended to use a simple sequenceDiagram with a dummy example - keep it minimal with at most 5 participants to ensure clarity. If participant name has space, use: `participant QP as Query Processing`. {mermaid_lang_note}.

- Then dive deeper into code for the internal implementation with references to files. Provide example code blocks, but make them similarly simple and beginner-friendly. Explain{instruction_lang_note}.

- IMPORTANT: When you need to refer to other core abstractions covered in other chapters, ALWAYS use proper Markdown links like this: [Chapter Title](filename.md). Use the Complete Tutorial Structure above to find the correct filename and the chapter title{link_lang_note}. Translate the surrounding text.

- Use mermaid diagrams to illustrate complex concepts (```mermaid``` format). {mermaid_lang_note}.

- Heavily use analogies and examples throughout{instruction_lang_note} to help beginners understand.

- End the chapter with a brief conclusion that summarizes what was learned{instruction_lang_note} and provides a transition to the next chapter{instruction_lang_note}. If there is a next chapter, use a proper Markdown link: [Next Chapter Title](next_chapter_filename){link_lang_note}.

- Ensure the tone is welcoming and easy for a newcomer to understand{tone_note}.

- Output *only* the Markdown content for this chapter.

Now, directly provide a super beginner-friendly Markdown output (DON'T need ```markdown``` tags):
"""
        chapter_content = call_llm(prompt)
        # Basic validation/cleanup
        actual_heading = f"# Chapter {chapter_num}: {abstraction_name}" # Use potentially translated name
        if not chapter_content.strip().startswith(f"# Chapter {chapter_num}"):
             # Add heading if missing or incorrect, trying to preserve content
             lines = chapter_content.strip().split('\n')
             if lines and lines[0].strip().startswith("#"): # If there's some heading, replace it
                 lines[0] = actual_heading
                 chapter_content = "\n".join(lines)
             else: # Otherwise, prepend it
                 chapter_content = f"{actual_heading}\n\n{chapter_content}"

        # Add the generated content to our temporary list for the next iteration's context
        self.chapters_written_so_far.append(chapter_content)

        return chapter_content # Return the Markdown string (potentially translated)

    def post(self, shared, prep_res, exec_res_list):
        # exec_res_list contains the generated Markdown for each chapter, in order
        shared["chapters"] = exec_res_list
        # Clean up the temporary instance variable
        del self.chapters_written_so_far
        print(f"Finished writing {len(exec_res_list)} chapters.")

class CombineTutorial(Node):
    def prep(self, shared):
        project_name = shared["project_name"]
        output_path = shared.get("output_dir", "output")  # Use provided output_dir directly, avoid nested project folder
        repo_url = shared.get("repo_url")  # Get the repository URL
        # language = shared.get("language", "english") # No longer needed for fixed strings

        # Get potentially translated data
        relationships_data = shared["relationships"] # {"summary": str, "details": [{"from": int, "to": int, "label": str}]} -> summary/label potentially translated
        chapter_order = shared["chapter_order"] # indices
        abstractions = shared["abstractions"]   # list of dicts -> name/description potentially translated
        chapters_content = shared["chapters"]   # list of strings -> content potentially translated

        # --- Generate Mermaid Diagram ---
        mermaid_lines = ["flowchart TD"]
        # Add nodes for each abstraction using potentially translated names
        for i, abstr in enumerate(abstractions):
            node_id = f"A{i}"
            # Use potentially translated name, sanitize for Mermaid ID and label
            sanitized_name = abstr['name'].replace('"', '')
            node_label = sanitized_name # Using sanitized name only
            mermaid_lines.append(f'    {node_id}["{node_label}"]') # Node label uses potentially translated name
        # Add edges for relationships using potentially translated labels
        for rel in relationships_data['details']:
            from_node_id = f"A{rel['from']}"
            to_node_id = f"A{rel['to']}"
            # Use potentially translated label, sanitize
            edge_label = rel['label'].replace('"', '').replace('\n', ' ') # Basic sanitization
            max_label_len = 30
            if len(edge_label) > max_label_len:
                edge_label = edge_label[:max_label_len-3] + "..."
            mermaid_lines.append(f'    {from_node_id} -- "{edge_label}" --> {to_node_id}') # Edge label uses potentially translated label

        mermaid_diagram = "\n".join(mermaid_lines)
        # --- End Mermaid ---

        # --- Prepare index.md content ---
        index_content = f"# Tutorial: {project_name}\n\n"
        index_content += f"{relationships_data['summary']}\n\n" # Use the potentially translated summary directly
        # Keep fixed strings in English
        index_content += f"**Source Repository:** [{repo_url}]({repo_url})\n\n"

        # Add Mermaid diagram for relationships (diagram itself uses potentially translated names/labels)
        index_content += "```mermaid\n"
        index_content += mermaid_diagram + "\n"
        index_content += "```\n\n"

        # Keep fixed strings in English
        index_content += f"## Chapters\n\n"

        chapter_files = []
        # Generate chapter links based on the determined order, using potentially translated names
        for i, abstraction_index in enumerate(chapter_order):
            # Ensure index is valid and we have content for it
            if 0 <= abstraction_index < len(abstractions) and i < len(chapters_content):
                abstraction_name = abstractions[abstraction_index]["name"] # Potentially translated name
                # Sanitize potentially translated name for filename
                safe_name = "".join(c if c.isalnum() else '_' for c in abstraction_name).lower()
                filename = f"{i+1:02d}_{safe_name}.md"
                index_content += f"{i+1}. [{abstraction_name}]({filename})\n" # Use potentially translated name in link text

                # Add attribution to chapter content (using English fixed string)
                chapter_content = chapters_content[i] # Potentially translated content
                if not chapter_content.endswith("\n\n"):
                    chapter_content += "\n\n"
                # Keep fixed strings in English
                chapter_content += f"---\n\nGenerated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)"

                # Store filename and corresponding content
                chapter_files.append({"filename": filename, "content": chapter_content})
            else:
                 print(f"Warning: Mismatch between chapter order, abstractions, or content at index {i} (abstraction index {abstraction_index}). Skipping file generation for this entry.")

        # Add attribution to index content (using English fixed string)
        index_content += f"\n\n---\n\nGenerated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)"

        return {
            "output_path": output_path,
            "index_content": index_content,
            "chapter_files": chapter_files # List of {"filename": str, "content": str}
        }

    def exec(self, prep_res):
        output_path = prep_res["output_path"]
        index_content = prep_res["index_content"]
        chapter_files = prep_res["chapter_files"]

        print(f"Combining tutorial into directory: {output_path}")
        # Rely on Node's built-in retry/fallback
        os.makedirs(output_path, exist_ok=True)

        # Write index.md
        index_filepath = os.path.join(output_path, "index.md")
        with open(index_filepath, "w", encoding="utf-8") as f:
            f.write(index_content)
        print(f"  - Wrote {index_filepath}")

        # Write chapter files
        for chapter_info in chapter_files:
            chapter_filepath = os.path.join(output_path, chapter_info["filename"])
            with open(chapter_filepath, "w", encoding="utf-8") as f:
                f.write(chapter_info["content"])
            print(f"  - Wrote {chapter_filepath}")

        return output_path # Return the final path


    def post(self, shared, prep_res, exec_res):
        shared["final_output_dir"] = exec_res # Store the output path
        print(f"\nTutorial generation complete! Files are in: {exec_res}")

########Context for utils/crawl_github_files.py ## this uses the call_llm.py to use the provided llm and model and api key
import requests
import base64
import os
import tempfile
import git
import time
import fnmatch
from typing import Union, Set, List, Dict, Tuple, Any
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import MaxRetryError
from requests.exceptions import RequestException
import sys
sys.setrecursionlimit(10000)
MAX_TRAVERSAL_DEPTH = 50

def crawl_github_files(
    repo_url, 
    token=None, 
    max_file_size: int = 1 * 1024 * 1024,  # 1 MB
    use_relative_paths: bool = False,
    include_patterns: Union[str, Set[str]] = None,
    exclude_patterns: Union[str, Set[str]] = None
):
    """
    Crawl files from a specific path in a GitHub repository at a specific commit.

    Args:
        repo_url (str): URL of the GitHub repository with specific path and commit
                        (e.g., 'https://github.com/microsoft/autogen/tree/e45a15766746d95f8cfaaa705b0371267bec812e/python/packages/autogen-core/src/autogen_core')
        token (str, optional): **GitHub personal access token.**
            - **Required for private repositories.**
            - **Recommended for public repos to avoid rate limits.**
            - Can be passed explicitly or set via the `GITHUB_TOKEN` environment variable.
        max_file_size (int, optional): Maximum file size in bytes to download (default: 1 MB)
        use_relative_paths (bool, optional): If True, file paths will be relative to the specified subdirectory
        include_patterns (str or set of str, optional): Pattern or set of patterns specifying which files to include (e.g., "*.py", {"*.md", "*.txt"}).
                                                       If None, all files are included.
        exclude_patterns (str or set of str, optional): Pattern or set of patterns specifying which files to exclude.
                                                       If None, no files are excluded.

    Returns:
        dict: Dictionary with files and statistics
    """
    # Convert single pattern to set
    if include_patterns and isinstance(include_patterns, str):
        include_patterns = {include_patterns}
    if exclude_patterns and isinstance(exclude_patterns, str):
        exclude_patterns = {exclude_patterns}

    def should_include_file(file_path: str, file_name: str) -> bool:
        """Determine if a file should be included based on patterns"""
        # If no include patterns are specified, include all files
        if not include_patterns:
            include_file = True
        else:
            # Check if file matches any include pattern
            include_file = any(fnmatch.fnmatch(file_name, pattern) for pattern in include_patterns)

        # If exclude patterns are specified, check if file should be excluded
        if exclude_patterns and include_file:
            # Exclude if file matches any exclude pattern
            exclude_file = any(fnmatch.fnmatch(file_path, pattern) for pattern in exclude_patterns)
            return not exclude_file

        return include_file

    # Detect SSH URL (git@ or .git suffix)
    is_ssh_url = repo_url.startswith("git@") or repo_url.endswith(".git")

    if is_ssh_url:
        # Clone repo via SSH to temp dir
        with tempfile.TemporaryDirectory() as tmpdirname:
            print(f"Cloning SSH repo {repo_url} to temp dir {tmpdirname} ...")
            try:
                repo = git.Repo.clone_from(repo_url, tmpdirname)
            except Exception as e:
                print(f"Error cloning repo: {e}")
                return {"files": {}, "stats": {"error": str(e)}}

            # Attempt to checkout specific commit/branch if in URL
            # Parse ref and subdir from SSH URL? SSH URLs don't have branch info embedded
            # So rely on default branch, or user can checkout manually later
            # Optionally, user can pass ref explicitly in future API

            # Walk directory
            files = {}
            skipped_files = []

            for root, dirs, filenames in os.walk(tmpdirname):
                for filename in filenames:
                    abs_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(abs_path, tmpdirname)

                    # Check file size
                    try:
                        file_size = os.path.getsize(abs_path)
                    except OSError:
                        continue

                    if file_size > max_file_size:
                        skipped_files.append((rel_path, file_size))
                        print(f"Skipping {rel_path}: size {file_size} exceeds limit {max_file_size}")
                        continue

                    # Check include/exclude patterns
                    if not should_include_file(rel_path, filename):
                        print(f"Skipping {rel_path}: does not match include/exclude patterns")
                        continue

                    # Read content
                    try:
                        with open(abs_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        files[rel_path] = content
                        print(f"Added {rel_path} ({file_size} bytes)")
                    except Exception as e:
                        print(f"Failed to read {rel_path}: {e}")

            return {
                "files": files,
                "stats": {
                    "downloaded_count": len(files),
                    "skipped_count": len(skipped_files),
                    "skipped_files": skipped_files,
                    "base_path": None,
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns,
                    "source": "ssh_clone"
                }
            }

    # Parse GitHub URL to extract owner, repo, commit/branch, and path
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")
    
    # Extract the basic components
    owner = path_parts[0]
    repo = path_parts[1]
    
    # Setup for GitHub API
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    # Setup requests session with retry/backoff
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    def fetch_branches(owner: str, repo: str):
        """Get branches of the repository"""

        url = f"https://api.github.com/repos/{owner}/{repo}/branches"
        response = session.get(url, headers=headers)

        if response.status_code == 404:
            if not token:
                print(f"Error 404: Repository not found or is private.\n"
                      f"If this is a private repository, please provide a valid GitHub token via the 'token' argument or set the GITHUB_TOKEN environment variable.")
            else:
                print(f"Error 404: Repository not found or insufficient permissions with the provided token.\n"
                      f"Please verify the repository exists and the token has access to this repository.")
            return []
            
        if response.status_code != 200:
            print(f"Error fetching the branches of {owner}/{path}: {response.status_code} - {response.text}")
            return []

        return response.json()

    def check_tree(owner: str, repo: str, tree: str):
        """Check the repository has the given tree"""

        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{tree}"
        response = session.get(url, headers=headers)

        return True if response.status_code == 200 else False 

    # Check if URL contains a specific branch/commit
    if len(path_parts) > 2 and 'tree' == path_parts[2]:
        join_parts = lambda i: '/'.join(path_parts[i:])

        branches = fetch_branches(owner, repo)
        branch_names = map(lambda branch: branch.get("name"), branches)

        # Fetching branches is not successfully
        if len(branches) == 0:
            return

        # To check branch name
        relevant_path = join_parts(3)

        # Find a match with relevant path and get the branch name
        filter_gen = (name for name in branch_names if relevant_path.startswith(name))
        ref = next(filter_gen, None)

        # If match is not found, check for is it a tree
        if ref == None:
            tree = path_parts[3]
            ref = tree if check_tree(owner, repo, tree) else None

        # If it is neither a tree nor a branch name
        if ref == None:
            print(f"The given path does not match with any branch and any tree in the repository.\n"
                  f"Please verify the path is exists.")
            return

        # Combine all parts after the ref as the path
        part_index = 5 if '/' in ref else 4
        specific_path = join_parts(part_index) if part_index < len(path_parts) else ""
    else:
        # Dont put the ref param to quiery
        # and let Github decide default branch
        ref = None
        specific_path = ""
    
    # Dictionary to store path -> content mapping
    files = {}
    skipped_files = []
    
    def fetch_contents(path):
        """Iterative fetch of repository contents to avoid recursion."""
        stack = [(path, 0)]  # (path, depth)
        while stack:
            current_path, depth = stack.pop()
            if depth > MAX_TRAVERSAL_DEPTH:
                print(f"Skipping {current_path}: exceeds max depth {MAX_TRAVERSAL_DEPTH}")
                continue
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{current_path}"
            params = {"ref": ref} if ref is not None else {}
            response = session.get(url, headers=headers, params=params)

            # Rate-limit handling
            if response.status_code == 403 and 'rate limit exceeded' in response.text.lower():
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = max(reset_time - time.time(), 0) + 1
                print(f"Rate limit exceeded. Waiting for {wait_time:.0f} seconds...")
                time.sleep(wait_time)
                stack.append((current_path, depth))
                continue
            # 404 handling
            if response.status_code == 404:
                if not token:
                    print(f"Error 404: Repository not found or is private.\n"
                          f"If this is a private repository, please provide a valid GitHub token via the 'token' argument or set the GITHUB_TOKEN environment variable.")
                elif not current_path and ref == 'main':
                    print(f"Error 404: Repository not found. Check if the default branch is not 'main'\n"
                          f"Try adding branch name to the request i.e. python main.py --repo https://github.com/username/repo/tree/master")
                else:
                    print(f"Error 404: Path '{current_path}' not found in repository or insufficient permissions with the provided token.\n"
                          f"Please verify the token has access to this repository and the path exists.")
                continue
            # Other errors
            if response.status_code != 200:
                print(f"Error fetching {current_path}: {response.status_code} - {response.text}")
                continue
            # Parse contents
            contents_list = response.json()
            if not isinstance(contents_list, list):
                contents_list = [contents_list]
            for item in contents_list:
                item_path = item["path"]
                # Relative path logic
                if use_relative_paths and specific_path:
                    if item_path.startswith(specific_path):
                        rel_path = item_path[len(specific_path):].lstrip('/')
                    else:
                        rel_path = item_path
                else:
                    rel_path = item_path
                if item["type"] == "file":
                    # File inclusion and size checks
                    if not should_include_file(rel_path, item["name"]):
                        print(f"Skipping {rel_path}: Does not match include/exclude patterns")
                        continue
                    file_size = item.get("size", 0)
                    if file_size > max_file_size:
                        skipped_files.append((item_path, file_size))
                        print(f"Skipping {rel_path}: File size ({file_size} bytes) exceeds limit ({max_file_size} bytes)")
                        continue
                    # Download file content
                    if item.get("download_url"):
                        file_response = session.get(item["download_url"], headers=headers)
                        content_length = int(file_response.headers.get('content-length', 0))
                        if content_length > max_file_size:
                            skipped_files.append((item_path, content_length))
                            print(f"Skipping {rel_path}: Content length ({content_length} bytes) exceeds limit ({max_file_size} bytes)")
                            continue
                        if file_response.status_code == 200:
                            files[rel_path] = file_response.text
                            print(f"Downloaded: {rel_path} ({file_size} bytes)")
                        else:
                            print(f"Failed to download {rel_path}: {file_response.status_code}")
                    else:
                        content_response = session.get(item["url"], headers=headers)
                        if content_response.status_code == 200:
                            content_data = content_response.json()
                            if content_data.get("encoding") == "base64" and "content" in content_data:
                                if len(content_data["content"]) * 0.75 > max_file_size:
                                    estimated_size = int(len(content_data["content"]) * 0.75)
                                    skipped_files.append((item_path, estimated_size))
                                    print(f"Skipping {rel_path}: Encoded content exceeds size limit")
                                    continue
                                files[rel_path] = base64.b64decode(content_data["content"]).decode('utf-8')
                                print(f"Downloaded: {rel_path} ({file_size} bytes)")
                            else:
                                print(f"Unexpected content format for {rel_path}")
                        else:
                            print(f"Failed to get content for {rel_path}: {content_response.status_code}")
                elif item["type"] == "dir":
                    # Skip excluded directories
                    if exclude_patterns and any(fnmatch.fnmatch(item_path, pat) for pat in exclude_patterns):
                        continue
                    stack.append((item_path, depth + 1))

    # Start crawling from the specified path
    try:
        # Pre-check: count total files via GitHub tree API and fallback if >1000
        try:
            meta_resp = session.get(f"https://api.github.com/repos/{owner}/{repo}")
            default_branch = meta_resp.json().get('default_branch') if meta_resp.status_code == 200 else None
            if default_branch:
                tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
                tree_resp = session.get(tree_url, headers=headers)
                if tree_resp.status_code == 200:
                    total_files = sum(1 for e in tree_resp.json().get('tree', []) if e.get('type') == 'blob')
                    if total_files > 1000:
                        print(f"Repository file count {total_files} exceeds threshold; falling back to git clone...", flush=True)
                        raise RuntimeError("File threshold exceeded")
        except Exception:
            # any failure or threshold exceeded triggers clone fallback
            raise
        fetch_contents(specific_path)
        source = 'api'
    except (RequestException, MaxRetryError, RuntimeError) as e:
        print(f"API crawling failed: {e}\nFalling back to local git clone...", flush=True)
        source = 'git_clone'
        # persistent clone logic
        cache_root = os.path.join(tempfile.gettempdir(), "crawl_github_cache")
        os.makedirs(cache_root, exist_ok=True)
        cache_dir = os.path.join(cache_root, f"{owner}_{repo.replace('/', '_')}")
        try:
            if not os.path.isdir(cache_dir):
                print(f"Cloning {repo_url} into cache {cache_dir} (shallow)...", flush=True)
                repo = git.Repo.clone_from(repo_url, cache_dir, depth=1, single_branch=True)
            else:
                print(f"Pulling updates for {repo_url} into {cache_dir}", flush=True)
                repo = git.Repo(cache_dir)
                repo.git.pull('--ff-only')
        except Exception as clone_e:
            print(f"Persistent clone failed: {clone_e}", flush=True)
            return {'files': files, 'stats': {'error': str(clone_e), 'source': 'git_clone'}}
        files.clear()
        skipped_files.clear()
        root_dir = cache_dir
        if use_relative_paths:
            root_dir = os.path.join(cache_dir, os.path.normpath(specific_path))
        # walk and read files from persistent clone
        for root_, dirs, filenames in os.walk(root_dir):
            for filename in filenames:
                abs_path = os.path.join(root_, filename)
                rel_path = os.path.relpath(abs_path, root_dir) if use_relative_paths else os.path.relpath(abs_path, cache_dir)
                if not should_include_file(rel_path, filename):
                    continue
                try:
                    file_size = os.path.getsize(abs_path)
                except OSError:
                    continue
                if file_size > max_file_size:
                    skipped_files.append((rel_path, file_size))
                    continue
                try:
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        files[rel_path] = f.read()
                        print(f"Cloned and added: {rel_path} ({file_size} bytes)", flush=True)
                except Exception as read_e:
                    print(f"Failed to read {rel_path}: {read_e}", flush=True)

    return {
        'files': files,
        'stats': {
            'downloaded_count': len(files),
            'skipped_count': len(skipped_files),
            'skipped_files': skipped_files,
            'base_path': specific_path if use_relative_paths else None,
            'include_patterns': include_patterns,
            'exclude_patterns': exclude_patterns,
            'source': source
        }
    }

# Example usage
if __name__ == "__main__":
    # Get token from environment variable (recommended for private repos)
    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        print("Warning: No GitHub token found in environment variable 'GITHUB_TOKEN'.\n"
              "Private repositories will not be accessible without a token.\n"
              "To access private repos, set the environment variable or pass the token explicitly.")
    
    repo_url = "https://github.com/pydantic/pydantic/tree/6c38dc93f40a47f4d1350adca9ec0d72502e223f/pydantic"
    
    # Example: Get Python and Markdown files, but exclude test files
    result = crawl_github_files(
        repo_url, 
        token=github_token,
        max_file_size=1 * 1024 * 1024,  # 1 MB in bytes
        use_relative_paths=True,  # Enable relative paths
        include_patterns={"*.py", "*.md"},  # Include Python and Markdown files
    )
    
    files = result["files"]
    stats = result["stats"]
    
    print(f"\nDownloaded {stats['downloaded_count']} files.")
    print(f"Skipped {stats['skipped_count']} files due to size limits or patterns.")
    print(f"Base path for relative paths: {stats['base_path']}")
    print(f"Include patterns: {stats['include_patterns']}")
    print(f"Exclude patterns: {stats['exclude_patterns']}")
    
    # Display all file paths in the dictionary
    print("\nFiles in dictionary:")
    for file_path in sorted(files.keys()):
        print(f"  {file_path}")
    
    # Example: accessing content of a specific file
    if files:
        sample_file = next(iter(files))
        print(f"\nSample file: {sample_file}")
        print(f"Content preview: {files[sample_file][:200]}...")

####### Context for utils/crawl_local_files.py ## this calls call_llm.py to use the provided llm and model and api key        

import os
import fnmatch

def crawl_local_files(directory, include_patterns=None, exclude_patterns=None, max_file_size=None, use_relative_paths=True):
    """
    Crawl files in a local directory with similar interface as crawl_github_files.
    
    Args:
        directory (str): Path to local directory
        include_patterns (set): File patterns to include (e.g. {"*.py", "*.js"})
        exclude_patterns (set): File patterns to exclude (e.g. {"tests/*"})
        max_file_size (int): Maximum file size in bytes
        use_relative_paths (bool): Whether to use paths relative to directory
        
    Returns:
        dict: {"files": {filepath: content}}
    """
    if not os.path.isdir(directory):
        raise ValueError(f"Directory does not exist: {directory}")
        
    files_dict = {}
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            # Get path relative to directory if requested
            if use_relative_paths:
                relpath = os.path.relpath(filepath, directory)
            else:
                relpath = filepath
                
            # Check if file matches any include pattern
            included = False
            if include_patterns:
                for pattern in include_patterns:
                    if fnmatch.fnmatch(relpath, pattern):
                        included = True
                        break
            else:
                included = True
                
            # Check if file matches any exclude pattern
            excluded = False
            if exclude_patterns:
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(relpath, pattern):
                        excluded = True
                        break
                        
            if not included or excluded:
                continue
                
            # Check file size
            if max_file_size and os.path.getsize(filepath) > max_file_size:
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                files_dict[relpath] = content
            except Exception as e:
                print(f"Warning: Could not read file {filepath}: {e}")
                
    return {"files": files_dict}

if __name__ == "__main__":
    print("--- Crawling parent directory ('..') ---")
    files_data = crawl_local_files("..", exclude_patterns={"*.pyc", "__pycache__/*", ".git/*", "output/*"})
    print(f"Found {len(files_data['files'])} files:")
    for path in files_data["files"]:
        print(f"  {path}")