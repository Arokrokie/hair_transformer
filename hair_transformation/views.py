import os
import uuid
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image
import json

from .forms import ImageUploadForm
from .models import HairTransformation, TransformationResult
from .utils.hair_ai import DjangoHairTransformation
import threading


class HomeView(View):
    def get(self, request):
        form = ImageUploadForm()
        return render(request, "hair_transformation/home.html", {"form": form})

    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the uploaded image
            hair_transformation = form.save(commit=False)
            hair_transformation.session_id = str(uuid.uuid4())
            hair_transformation.save()

            # Process the image
            return redirect(
                "processing_view", session_id=hair_transformation.session_id
            )

        return render(request, "hair_transformation/home.html", {"form": form})


class ProcessingView(View):
    def get(self, request, session_id):
        try:
            hair_transformation = HairTransformation.objects.get(session_id=session_id)

            # If results already exist, redirect immediately
            if hair_transformation.results.exists():
                return redirect("results_view", session_id=session_id)

            # If processing already in progress, render the processing page so client can poll
            if (
                hair_transformation.progress
                and hair_transformation.progress > 0
                and hair_transformation.progress < 100
            ):
                return render(
                    request,
                    "hair_transformation/processing.html",
                    {"session_id": session_id},
                )

            # Otherwise, kick off background processing and render the processing page immediately
            processor = DjangoHairTransformation()

            # mark as starting
            hair_transformation.progress = 1
            hair_transformation.processing_step = "queued"
            hair_transformation.save(update_fields=["progress", "processing_step"])

            def run_processing():
                try:
                    image_path = hair_transformation.original_image.path
                    results = processor.process_image(image_path, session_id)

                    if not results:
                        hair_transformation.processing_step = "failed"
                        hair_transformation.save(update_fields=["processing_step"])
                        return

                    # Save analysis data
                    hair_transformation.skin_tone = results["analysis_data"].get(
                        "skin_tone"
                    )
                    hair_transformation.ethnicity = results["analysis_data"].get(
                        "ethnicity"
                    )
                    hair_transformation.face_shape = results["analysis_data"].get(
                        "face_shape"
                    )
                    hair_transformation.hair_length = results["analysis_data"].get(
                        "hair_length"
                    )
                    hair_transformation.hair_texture = results["analysis_data"].get(
                        "hair_texture"
                    )
                    hair_transformation.style_recommendations = results.get(
                        "recommendations", {}
                    ).get("styles")
                    hair_transformation.color_recommendations = results.get(
                        "recommendations", {}
                    ).get("colors")

                    # Save analysis images
                    try:
                        hair_analysis_file = processor.pil_to_django_file(
                            results["images"]["hair_analysis"],
                            f"{session_id}_hair_analysis.png",
                        )
                        hair_transformation.hair_analysis_image.save(
                            f"{session_id}_hair_analysis.png", hair_analysis_file
                        )
                    except Exception:
                        pass

                    # Save segmentation mask if present
                    try:
                        seg_mask = results["images"].get("segmentation_mask")
                        if seg_mask is not None:
                            hair_mask_file = processor.pil_to_django_file(
                                seg_mask, f"{session_id}_hair_mask.png"
                            )
                            hair_transformation.hair_mask_image.save(
                                f"{session_id}_hair_mask.png", hair_mask_file
                            )
                    except Exception:
                        pass

                    # Save hair coverage percent (if present)
                    try:
                        hair_coverage = results.get("analysis_data", {}).get(
                            "hair_coverage"
                        )
                        if hair_coverage is not None:
                            hair_transformation.hair_coverage = float(hair_coverage)
                    except Exception:
                        pass

                    try:
                        face_analysis_file = processor.pil_to_django_file(
                            results["images"]["face_analysis"],
                            f"{session_id}_face_analysis.png",
                        )
                        hair_transformation.face_analysis_image.save(
                            f"{session_id}_face_analysis.png", face_analysis_file
                        )
                    except Exception:
                        pass

                    hair_transformation.save()

                    # Save transformation results
                    for transformation in results["images"].get("transformations", []):
                        try:
                            transformed_file = processor.pil_to_django_file(
                                transformation["image"],
                                f"{session_id}_{transformation['style_type']}_{uuid.uuid4().hex[:8]}.png",
                            )

                            TransformationResult.objects.create(
                                hair_transformation=hair_transformation,
                                style_name=transformation.get("title"),
                                style_type=transformation.get("style_type"),
                                transformed_image=transformed_file,
                            )
                        except Exception:
                            continue

                    # mark complete
                    hair_transformation.progress = 100
                    hair_transformation.processing_step = "complete"
                    hair_transformation.save(
                        update_fields=["progress", "processing_step"]
                    )

                except Exception:
                    try:
                        hair_transformation.processing_step = "failed"
                        hair_transformation.save(update_fields=["processing_step"])
                    except Exception:
                        pass

            t = threading.Thread(target=run_processing, daemon=True)
            t.start()

            return render(
                request,
                "hair_transformation/processing.html",
                {"session_id": session_id},
            )

        except HairTransformation.DoesNotExist:
            return render(
                request,
                "hair_transformation/error.html",
                {"error": "Session not found."},
            )
        except Exception as e:
            return render(
                request,
                "hair_transformation/error.html",
                {"error": f"Processing error: {str(e)}"},
            )


class ResultsView(View):
    def get(self, request, session_id):
        try:
            hair_transformation = HairTransformation.objects.get(session_id=session_id)
            transformation_results = hair_transformation.results.all()

            # Separate long and short styles
            long_styles = transformation_results.filter(style_type="Long")
            short_styles = transformation_results.filter(style_type="Short")
            # Prepare a display list: 2 long + 2 short if available
            transformations_display = []
            try:
                transformations_display.extend(list(long_styles[:2]))
            except Exception:
                pass
            try:
                transformations_display.extend(list(short_styles[:2]))
            except Exception:
                pass

            context = {
                "transformation": hair_transformation,
                "long_styles": long_styles,
                "short_styles": short_styles,
                "transformations_display": transformations_display,
                "analysis_data": {
                    "skin_tone": hair_transformation.skin_tone,
                    "ethnicity": hair_transformation.ethnicity,
                    "face_shape": hair_transformation.face_shape,
                    "hair_length": hair_transformation.hair_length,
                    "hair_texture": hair_transformation.hair_texture,
                },
            }

            # Prepare color swatches (name + hex) for template display
            name_to_hex = {
                "Jet Black": "#000000",
                "Natural Black": "#0b0b0b",
                "Blue Black": "#0b0f1a",
                "Burgundy": "#800020",
                "Purple": "#6f42c1",
                "Brown Black": "#5a3e36",
                "Honey Blonde": "#DDB67D",
                "Golden Brown": "#8B5C42",
                "Ash Brown": "#7B6D6A",
                "Caramel": "#C68E58",
            }

            raw_colors = getattr(hair_transformation, "color_recommendations", []) or []
            color_swatches = []
            for c in raw_colors:
                if isinstance(c, str) and c.startswith("#"):
                    color_swatches.append({"name": c, "hex": c})
                else:
                    hex_code = name_to_hex.get(c)
                    color_swatches.append({"name": c, "hex": hex_code})

            # add to context
            context["color_swatches"] = color_swatches

            return render(request, "hair_transformation/results.html", context)

        except HairTransformation.DoesNotExist:
            return render(
                request,
                "hair_transformation/error.html",
                {"error": "Results not found."},
            )


class AjaxProcessingView(View):
    def get(self, request, session_id):
        """AJAX endpoint to check processing status"""
        try:
            hair_transformation = HairTransformation.objects.get(session_id=session_id)
            results_exist = hair_transformation.results.exists()
            return JsonResponse(
                {
                    "processed": results_exist,
                    "status": "complete" if results_exist else "processing",
                    "progress": int(getattr(hair_transformation, "progress", 0) or 0),
                    "step": getattr(hair_transformation, "processing_step", ""),
                }
            )
        except HairTransformation.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)
