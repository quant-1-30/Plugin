# spider/encoders.py
import json
import numpy as np
from datetime import datetime, date

# from scrapy.utils.serialize import ScrapyJSONEncoder

class CustomFeedJsonEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return o.decode('utf-8', errors='ignore')
            
        if isinstance(o, (np.integer, np.int64, np.int32)):
            return int(o)
        if isinstance(o, (np.floating, np.float64, np.float32)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
            
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)

