def make_exe():
    # Obtain the default Python distribution for the target
    dist = default_python_distribution()
    
    # Create packaging policy
    policy = dist.make_python_packaging_policy()
    
    # Configure Python interpreter settings
    python_config = dist.make_python_interpreter_config()
    python_config.run_module = "your_main_module"  # Replace with your main module

    # Automatically detect target based on build host
    target_triple = HOST_TRIPLE

    # Create the executable
    exe = dist.to_python_executable(
        name="your_app_name",  # Replace with your app name
        target_triple=target_triple,
        packaging_policy=policy,
        config=python_config,
    )

    # Add your project's Python files
    exe.add_python_resources(
        exe.read_package_root(
            path=".",  # Path to your project's Python files
            packages=["your_package_name"],  # Replace with your package name
        )
    )

    # Add dependencies from requirements.txt
    exe.add_python_resources(exe.pip_install(["-r", "requirements.txt"]))

    return exe

register_target("exe", make_exe)
resolve_targets()