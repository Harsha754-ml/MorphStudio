import os
import subprocess
from pathlib import Path
import json

# Constants
PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "renders"
OUTPUT_DIR.mkdir(exist_ok=True)

class StudioCore:
    """The engine that handles Multi-SVG scene generation and execution."""

    SCENE_TEMPLATE = """
from manim import *

class StudioScene(Scene):
    def construct(self):
        bg_color = "{bg_color}"
        self.camera.background_color = bg_color
        
        assets = {assets_json}
        
        # Easing Map
        easings = {{
            "Smooth": rate_functions.smooth,
            "Linear": rate_functions.linear,
            "InExpo": rate_functions.exponential_decay,
            "InBounce": rate_functions.rush_into, 
            "Elastic": rate_functions.rush_from,
            "EaseIn": rate_functions.ease_in_sine,
            "EaseOut": rate_functions.ease_out_sine,
            "EaseInOut": rate_functions.ease_in_out_sine,
            "SlowIn": rate_functions.rush_into,
            "SlowOut": rate_functions.rush_from,
        }}
        
        current_time = 0
        last_asset_end = 0
        
        for asset in assets:
            initial = asset["initial_state"]
            final = asset["final_state"]
            
            # 1. Setup Source Object
            svg_a = SVGMobject(initial.get("svg") or asset["path"], fill_opacity=1, stroke_width=1)
            
            # Normalize Scaling
            def normalize(obj, state):
                max_dim = max(obj.width, obj.height)
                if max_dim > 0:
                    obj.scale(1.7777777 / max_dim)
                obj.scale(state.get("scale", 1.0))
                obj.rotate(state.get("rotation", 0) * DEGREES)
                obj.move_to([state.get("x", 0), state.get("y", 0), 0])
                obj.set_opacity(state.get("opacity", 1.0))
            
            normalize(svg_a, initial)
            
            # Timing
            duration = asset.get("duration", 2.0)
            delay = asset.get("delay", 0)
            start_time = (last_asset_end + delay) if asset.get("sequence_mode", False) else delay
            
            if start_time > current_time:
                self.wait(start_time - current_time)
                current_time = start_time
            
            easing_func = easings.get(asset.get("easing", "Smooth"), smooth)
            anim_type = asset.get("anim", "Path")
            
            # 2. Setup Target State for simple animations
            if anim_type == "Morph":
                svg_b = SVGMobject(final.get("svg") or asset["path"], fill_opacity=1, stroke_width=1)
                normalize(svg_b, final)
                self.add(svg_a)
                self.play(ReplacementTransform(svg_a, svg_b), run_time=duration, rate_func=easing_func)
            
            elif anim_type == "Path":
                self.add(svg_a)
                self.play(
                    svg_a.animate.move_to([final["x"], final["y"], 0])
                                 .scale(final["scale"] / initial["scale"])
                                 .rotate((final["rotation"] - initial["rotation"]) * DEGREES),
                    run_time=duration, rate_func=easing_func
                )
            
            elif anim_type == "Fade":
                svg_a.set_opacity(0)
                self.play(FadeIn(svg_a, target_position=[final["x"], final["y"], 0]), run_time=duration)
                
            elif anim_type == "Draw":
                self.play(Create(svg_a), run_time=duration/2)
                self.play(svg_a.animate.move_to([final["x"], final["y"], 0]), run_time=duration/2, rate_func=easing_func)
            
            else:
                self.add(svg_a)
                
            last_asset_end = current_time + duration
            current_time = last_asset_end
            
        self.wait(2)
"""

    @staticmethod
    def generate_scene_code(global_params, assets):
        """Injects UI parameters and the asset list into the template."""
        assets_repr = repr(assets)
        return StudioCore.SCENE_TEMPLATE.format(
            bg_color=global_params["bg_color"],
            fit_padding=global_params.get("fit_padding", 1.5),
            assets_json=assets_repr
        )

    @staticmethod
    def run_render(global_params, assets, quality="l", callback=None):
        """Generates a temp file, runs Manim, and cleans up."""
        temp_file = PROJECT_ROOT / "_studio_temp.py"
        code = StudioCore.generate_scene_code(global_params, assets)
        temp_file.write_text(code)

        cmd = [
            "manim",
            f"-pq{quality}",
            str(temp_file),
            "StudioScene",
            "--media_dir", str(OUTPUT_DIR),
            "--write_to_movie"
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=str(PROJECT_ROOT)
        )

        if callback:
            for line in process.stdout:
                callback(line)
        
        process.wait()
        if temp_file.exists():
            temp_file.unlink()
            
        return process.returncode == 0
