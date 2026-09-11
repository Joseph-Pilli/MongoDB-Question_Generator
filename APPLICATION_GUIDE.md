# MongoDB Question Generator

## What the application does

This Flask application turns a MongoDB assignment or concept description into a
complete assessment package. Each generated package contains:

- `_prefilled`: the student starter files;
- `_solution`: a completed reference implementation; and
- `_tests`: automated tests for the generated solution.

The application uses a fixed MongoDB syllabus to keep generated questions within
scope. The syllabus covers schema design, CRUD, relationships, aggregation,
indexing, validation, pagination/sorting, and error handling.

## Running the application

1. Install dependencies with `pip install -r requirements.txt`.
2. Start the server with `python app.py`.
3. Open `http://localhost:5000`.
4. Enter an OpenAI API key in the **API key** field and select **Save key**.

The key is sent to the local Flask server, written to `OPENAI_API_KEY` in the
project `.env` file, and loaded into the running process. It is masked in the
browser and is not returned by the save endpoint. Use HTTPS and restrict access
when running the application anywhere other than a trusted local machine.

## Normal workflow

1. Paste an assignment or upload a `.txt`, `.md`, `.pdf`, or `.docx` file.
2. Optionally enter a question title, domain, student implementation files,
   and scaffold files.
3. Select **Analyze assignment**. The analyzer identifies syllabus coverage and
   flags concepts outside the syllabus.
4. Review the coverage grid and select the concepts to assess.
5. Select **Generate prefilled + solution + tests**. The generated package is
   written under `output/` and shown in the preview.
6. Inspect the three folder tabs, then download the ZIP package.

Analysis is fast and local. Generation calls the configured OpenAI model and
can take longer depending on the request and API response.

## Evaluation sets

The detailed test plan is in [EVAL_SETS.md](EVAL_SETS.md). It is organized into
these checks:

- **A:** application smoke tests, including startup, analysis, generation, and
  missing-key behavior;
- **B:** requested student/scaffold file structure;
- **C:** alignment with each syllabus concept;
- **D:** generated README quality;
- **E:** generated test-file quality and test identifiers;
- **F:** sample demo prompts, including an out-of-scope prompt;
- **G:** running `npm test` against generated solution packages; and
- **H:** comparison of this workflow with manual question creation.

For a quick acceptance run, start with Set A, generate the three sample prompts
in Set F, and run Set G for each package. A release-ready result is defined in
`EVAL_SETS.md` as at least 80% overall and passing solution tests for F1, F2,
and F3.