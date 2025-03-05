import flet as ft
import subprocess
import os
import shlex
from typing import List
import logging
import asyncio


class MRCProcessorGUI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "MRC Tomogram Processor"
        self.page.window_width = 800
        self.page.window_height = 800

        # Create file picker instances
        self.directory_picker = ft.FilePicker()
        self.page.overlay.extend([self.directory_picker])

        self.setup_ui()
        self.setup_logging()

    def setup_logging(self):
        self.log_output = ft.ListView(expand=True, spacing=10, padding=20)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[self.FletLogHandler(self.page, self.log_output)],
        )

    class FletLogHandler(logging.Handler):
        def __init__(self, page, log_output):
            super().__init__()
            self.page = page
            self.log_output = log_output

        def emit(self, record):
            log_entry = self.format(record)
            self.log_output.controls.append(ft.Text(log_entry))
            self.page.update()

    def setup_ui(self):
        # Input controls
        self.input_dir = ft.TextField(label="Input Directory", expand=True)
        self.output_dir = ft.TextField(label="Output Directory", expand=True)

        # Directory selection buttons
        input_button = ft.ElevatedButton(
            "Select Input Directory",
            on_click=lambda _: self.log_and_open_picker("input"),
        )

        output_button = ft.ElevatedButton(
            "Select Output Directory",
            on_click=lambda _: self.log_and_open_picker("output"),
        )

        # Processing parameters
        self.fps = ft.TextField(label="FPS", value="30.0")
        self.clip_limit = ft.TextField(label="Clip Limit", value="2.0")
        self.tile_grid_size = ft.TextField(label="Tile Grid Size", value="8")
        self.codec = ft.Dropdown(
            label="Codec",
            options=[ft.dropdown.Option("MJPG"), ft.dropdown.Option("mp4v")],
            value="MJPG",
        )
        self.playback = ft.Dropdown(
            label="Playback Direction",
            options=[
                ft.dropdown.Option("forward"),
                ft.dropdown.Option("forward-backward"),
            ],
            value="forward-backward",
        )

        # Discard options
        self.discard_start = ft.TextField(label="Discard Start", width=150)
        self.discard_end = ft.TextField(label="Discard End", width=150)
        self.discard_pct_start = ft.TextField(label="Discard % Start", width=150)
        self.discard_pct_end = ft.TextField(label="Discard % End", width=150)

        # Additional options
        self.save_png = ft.Checkbox(label="Save PNGs", value=False)
        self.output_size = ft.TextField(label="Output Size", value="1024")

        # Progress and logs
        self.progress = ft.ProgressBar(width=800, value=0)
        self.log_display = ft.ListView(expand=True)

        # Action buttons
        start_button = ft.ElevatedButton(
            "Start Processing", on_click=self.start_processing, icon=ft.icons.PLAY_ARROW
        )
        clear_button = ft.ElevatedButton(
            "Clear Logs", on_click=lambda _: self.clear_logs(), icon=ft.icons.CLEAR
        )

        # Add everything to the page
        self.page.add(
            ft.Row(
                [input_button, output_button], alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Row([self.input_dir, self.output_dir]),
            ft.Card(
                ft.Container(
                    ft.Column(
                        [
                            ft.Text("Processing Parameters:", size=18),
                            ft.Row([self.fps, self.clip_limit, self.tile_grid_size]),
                            ft.Row([self.codec, self.playback]),
                            ft.Row([self.save_png, self.output_size]),
                        ],
                        spacing=10,
                    ),
                    padding=20,
                )
            ),
            ft.Card(
                ft.Container(
                    ft.Column(
                        [
                            ft.Text("Discard Options:", size=18),
                            ft.Row(
                                [
                                    ft.Text("Slice Range:"),
                                    self.discard_start,
                                    self.discard_end,
                                ]
                            ),
                            ft.Row(
                                [
                                    ft.Text("Percentage Range:"),
                                    self.discard_pct_start,
                                    self.discard_pct_end,
                                ]
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=20,
                )
            ),
            ft.Row([start_button, clear_button], alignment=ft.MainAxisAlignment.CENTER),
            self.progress,
            ft.Divider(),
            ft.Text("Processing Log:", size=20),
            self.log_display,
        )

    def log_and_open_picker(self, field_type: str):
        """Open the FilePicker and log the action."""
        logging.info(f"Opening directory picker for {field_type}")
        if field_type == "input":
            self.directory_picker.on_result = self.on_directory_selected("input")
        else:
            self.directory_picker.on_result = self.on_directory_selected("output")
        self.directory_picker.get_directory_path()
        self.page.update()

    def on_directory_selected(self, field_type: str):
        """Handle directory selection event."""

        def handler(e: ft.FilePickerResultEvent):
            if e.path:
                if field_type == "input":
                    self.input_dir.value = e.path
                else:
                    self.output_dir.value = e.path
                logging.info(f"Selected {field_type} directory: {e.path}")
                self.page.update()

        return handler

    def clear_logs(self):
        self.log_display.controls.clear()
        self.page.update()

    async def start_processing(self, e):
        cmd = self.build_command()
        if not cmd:
            return

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )

            while True:
                output = await process.stdout.readline()
                if not output:
                    break
                self.log_display.controls.append(ft.Text(output.decode().strip()))
                self.page.update()

            await process.wait()
            if process.returncode != 0:
                self.log_error(f"Process failed with code {process.returncode}")
            else:
                logging.info("Processing completed successfully")

        except Exception as e:
            self.log_error(f"Error: {str(e)}")

    def build_command(self) -> List[str]:
        base_cmd = ["python", "mrc2movie.py"]

        if not os.path.isdir(self.input_dir.value):
            self.log_error("Invalid input directory")
            return []
        if not self.output_dir.value:
            self.log_error("Output directory required")
            return []

        cmd = base_cmd + [
            shlex.quote(self.input_dir.value),
            shlex.quote(self.output_dir.value),
            "--fps",
            self.fps.value,
            "--clip_limit",
            self.clip_limit.value,
            "--tile_grid_size",
            self.tile_grid_size.value,
            "--codec",
            self.codec.value,
            "--playback",
            self.playback.value,
            "--output_size",
            self.output_size.value,
        ]

        if self.save_png.value:
            cmd.append("--png")

        if self.discard_start.value and self.discard_end.value:
            cmd += ["--discard_range", self.discard_start.value, self.discard_end.value]
        elif self.discard_pct_start.value and self.discard_pct_end.value:
            cmd += [
                "--discard_percentage",
                self.discard_pct_start.value,
                self.discard_pct_end.value,
            ]

        return cmd

    def log_error(self, message):
        logging.error(message)
        self.page.snack_bar = ft.SnackBar(ft.Text(message))
        self.page.snack_bar.open = True
        self.page.update()


def main(page: ft.Page):
    MRCProcessorGUI(page)


if __name__ == "__main__":
    ft.app(target=main)
