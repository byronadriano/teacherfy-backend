# TeacherfyAI

A simple Flask app that creates lesson plans and PowerPoint presentations using AI.

## Project Structure
```
teacherfy/
├── src/
│   ├── app.py                  # Main Flask application
│   ├── presentation.py         # PowerPoint generation code
│   ├── slides.py              # Slide processing code
│   └── templates/
│       └── base_template.pptx  # Base PowerPoint template
├── examples/                   # Example files
│   └── equivalent_fractions_outline.json
├── .env                       # Your secret keys and settings
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Setup Guide

1. Install Python requirements:
```bash
pip install -r requirements.txt
```

2. Create a file called `.env` in the main folder and add your OpenAI key:
```
OPENAI_API_KEY=your-key-here
```

3. Run the app:
```bash
python src/app.py
```

## How It Works

### `app.py`
- Contains the Flask routes (`/outline` and `/generate`)
- Handles API requests and responses
- Connects to OpenAI

To modify the prompts or add new routes:
1. Find the route you want to change (like `/outline`)
2. Update the prompt text or add a new route following the same pattern

### `presentation.py`
- Creates the PowerPoint files
- Calls `slides.py` to process the outline

To modify presentation generation:
1. Update the `generate_presentation()` function
2. Be careful with the file handling code!

### `slides.py`
- Processes the outline text into slide content
- Creates individual PowerPoint slides

To modify slide layouts:
1. Update the `parse_outline_to_structured_content()` function for outline changes
2. Update the `create_presentation()` function for PowerPoint changes

## Common Tasks

### Adding a New Language
1. Add the language to the `languages` list in the frontend
2. Update the prompt in `app.py` to handle the new language

### Modifying the PowerPoint Template
1. Update `templates/base_template.pptx`
2. Make sure it has:
   - A title slide
   - A content slide layout
   - A two-column layout

### Changing the Slide Format
1. Update the prompt in `app.py` to change what content is generated
2. Update `slides.py` to handle the new format

### Error Fixing
Common issues and solutions:
- If OpenAI isn't working: Check your `.env` file and API key
- If PowerPoint isn't generating: Check the `templates` folder has `base_template.pptx`
- If slides look wrong: Check the outline format in `slides.py`

## Need Help?
1. Check the error message in your terminal
2. Make sure all files are in the right places
3. Check your API key is correct
4. Make sure your PowerPoint template exists

## Testing
Test the app by:
1. Running it locally
2. Using the example inputs
3. Checking the generated PowerPoints

Remember: Make small changes and test them before moving on!
