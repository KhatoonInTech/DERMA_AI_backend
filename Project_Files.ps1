#Go to Poweshell terminal and run ./Project_Files.ps1 

New-Item -Path "Agents" -ItemType Directory

# Create main files
New-Item -Path "__init__.py" -ItemType File
New-Item -Path "app.py" -ItemType File
New-Item -Path "CONFIGURATION.py" -ItemType File
New-Item -Path "Initialization.py" -ItemType File
New-Item -Path ".env" -ItemType File
New-Item -Path "requirements.txt" -ItemType File
New-Item -Path "README.md" -ItemType File

# Create files in the Agents directory
New-Item -Path "Agents\UserIntakeAgent.py" -ItemType File
New-Item -Path "Agents\SearchEngineAgent.py" -ItemType File
New-Item -Path "Agents\Diagnosis.py" -ItemType File
New-Item -Path "Agents\ReportingGenerationAgent.py" -ItemType File
New-Item -Path "Agents\ReportingAnalysisAgent.py" -ItemType File
New-Item -Path "Agents\chatbot.py" -ItemType File