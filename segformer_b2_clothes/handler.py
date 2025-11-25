from typing import Dict, List, Any
from PIL import Image
from io import BytesIO
from transformers import AutoModelForSemanticSegmentation, AutoFeatureExtractor
import base64
import torch
from torch import nn

class EndpointHandler():
    def __init__(self, path="."):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = AutoModelForSemanticSegmentation.from_pretrained(path).to(self.device).eval()
        self.feature_extractor = AutoFeatureExtractor.from_pretrained(path)
    
    def __call__(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
       data args:
            images (:obj:`PIL.Image`)
            candiates (:obj:`list`)
      Return:
            A :obj:`list`:. The list contains items that are dicts should be liked {"label": "XXX", "score": 0.82}
        """
        inputs = data.pop("inputs", data)

        # decode base64 image to PIL
        image = Image.open(BytesIO(base64.b64decode(inputs['image'])))
        
        # preprocess image
        encoding = self.feature_extractor(images=image, return_tensors="pt")
        pixel_values = encoding["pixel_values"].to(self.device)
        with torch.no_grad():
            outputs = self.model(pixel_values=pixel_values)
        logits = outputs.logits
        upsampled_logits = nn.functional.interpolate(logits, 
            size=image.size[::-1],
            mode="bilinear",
            align_corners=False,)
        pred_seg = upsampled_logits.argmax(dim=1)[0]
        return pred_seg.tolist()
