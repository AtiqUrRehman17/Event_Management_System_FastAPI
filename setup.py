"""
Setup script for development environment.
One-command setup:  python setup.py
"""
import os
import secrets
import shutil


def main():
    env_example = ".env.example"
    env_file = ".env"

    # Step 1: Copy .env.example → .env if missing
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            shutil.copy2(env_example, env_file)
            print(f"✓ Created {env_file} from {env_example}")
        else:
            print(f"✗ {env_example} not found. Are you in the project root?")
            return
    else:
        print(f"• {env_file} already exists, skipping copy")

    # Step 2: Generate secure SECRET_KEY
    new_key = secrets.token_urlsafe(32)
    with open(env_file, "r") as f:
        lines = f.readlines()

    replaced = False
    for i, line in enumerate(lines):
        if line.strip().startswith("SECRET_KEY="):
            lines[i] = f'SECRET_KEY="{new_key}"\n'
            replaced = True
            break

    with open(env_file, "w") as f:
        f.writelines(lines)

    if replaced:
        print(f"✓ Generated new SECRET_KEY in {env_file}")
    else:
        print(f"• Could not find SECRET_KEY in {env_file}, appending it")
        with open(env_file, "a") as f:
            f.write(f'\nSECRET_KEY="{new_key}"\n')

    # Step 3: Summary
    print()
    print("=" * 60)
    print("  Environment setup complete!")
    print(f"  .env file: {env_file}")
    print("  Run the app:  python run.py")
    print("  Run tests:    pytest")
    print("=" * 60)


if __name__ == "__main__":
    main()
