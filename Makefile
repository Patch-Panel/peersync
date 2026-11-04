# Available commands
.PHONY: format build clean

# Format all C++ source and header files
format:
	@echo "Formatting C++ files..."
	@find . -type f \( -name '*.cpp' -o -name '*.h' -o -name '*.hpp' \) \
		-not -path './build/*' \
		-exec clang-format -i {} +
	@echo "Formatting complete!"

# Configure and build the project
build:
	@echo "Configuring project..."
	@cmake -S . -B build
	@echo "Compiling..."
	@cmake --build build
	@echo "Build complete!"

# Remove generated build files
clean:
	@echo "Cleaning build directory..."
	@rm -rf build
	@echo "Clean complete!"
