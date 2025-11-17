from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import base64
import logging

try:
    import cv2  # type: ignore
    import numpy as np  # type: ignore
except Exception:
    cv2 = None
    np = None


class Algorithm:
    def __init__(self, algo_type: str, params: Dict[str, Any]):
        self.algo_type = algo_type
        self.params = params or {}

    def run(self, image: Any, step: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "OK", "ng_regions": []}


class TemplateMatchAlgorithm(Algorithm):
    def run(self, image: Any, step: Dict[str, Any]) -> Dict[str, Any]:
        logger = logging.getLogger(__name__)
        if cv2 is None or np is None:
            logger.warning("cv2 or numpy not available, detection bypassed as OK")
            return {"status": "OK", "ng_regions": []}
        template_path = step.get("template_image") or self.params.get("template_image")
        threshold = float(step.get("tolerance", {}).get("min_match_score", self.params.get("threshold", 0.85)))
        tpl_np = step.get("template_image_np")
        if not template_path and tpl_np is None:
            logger.warning("no template provided, NG")
            return {"status": "NG", "ng_regions": []}
        try:
            if isinstance(image, np.ndarray):
                src = image
            else:
                src = np.array(image)
            if tpl_np is not None:
                tpl = cv2.cvtColor(tpl_np, cv2.COLOR_BGR2GRAY)
            else:
                tpl = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
            if tpl is None:
                logger.warning("failed to load template, NG")
                return {"status": "NG", "ng_regions": []}
            roi = step.get("roi") or step.get("relative_roi")
            if isinstance(roi, (list, tuple)) and len(roi) == 4:
                rx, ry, rw, rh = [int(v) for v in roi]
                rx = max(0, rx)
                ry = max(0, ry)
                rw = max(1, rw)
                rh = max(1, rh)
                x2 = min(src.shape[1], rx + rw)
                y2 = min(src.shape[0], ry + rh)
                crop = src[ry:y2, rx:x2]
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
            res = cv2.matchTemplate(gray, tpl, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            logger.info(f"template_match score={max_val:.4f} threshold={threshold:.4f} roi={roi}")
            if max_val >= threshold:
                logger.info("detection PASS")
                return {"status": "OK", "ng_regions": []}
            h, w = tpl.shape[:2]
            x1, y1 = max_loc
            x2, y2 = x1 + w, y1 + h
            if isinstance(roi, (list, tuple)) and len(roi) == 4:
                rx, ry, rw, rh = [int(v) for v in roi]
                x1 += rx
                y1 += ry
                x2 += rx
                y2 += ry
            logger.info("detection FAIL")
            return {"status": "NG", "ng_regions": [{"box_coords": [x1, y1, x2, y2]}]}
        except Exception:
            logger.exception("template_match error")
            return {"status": "NG", "ng_regions": []}


class KeypointFeatureAlgorithm(Algorithm):
    def run(self, image: Any, step: Dict[str, Any]) -> Dict[str, Any]:
        logger = logging.getLogger(__name__)
        if cv2 is None or np is None:
            logger.warning("cv2 or numpy not available, feature detection NG")
            return {"status": "NG", "ng_regions": []}
        try:
            src = image if isinstance(image, np.ndarray) else np.array(image)
            roi = step.get("roi") or step.get("relative_roi")
            if isinstance(roi, (list, tuple)) and len(roi) == 4:
                rx, ry, rw, rh = [int(v) for v in roi]
                rx = max(0, rx); ry = max(0, ry); rw = max(1, rw); rh = max(1, rh)
                x2 = min(src.shape[1], rx + rw); y2 = min(src.shape[0], ry + rh)
                crop = src[ry:y2, rx:x2]
            else:
                crop = src
            tpl_np = step.get("template_image_np")
            if tpl_np is None:
                img_b64 = step.get("image_base64")
                if isinstance(img_b64, str) and img_b64:
                    tpl_np = _decode_image_base64(img_b64)
            if tpl_np is None:
                logger.warning("no template image; NG")
                return {"status": "NG", "ng_regions": [{"box_coords": [rx, ry, rx+rw, ry+rh]}] if isinstance(roi, (list, tuple)) and len(roi)==4 else []}

            algo = str(self.algo_type).lower()
            params = self.params.copy()
            gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            gray_tpl = cv2.cvtColor(tpl_np, cv2.COLOR_BGR2GRAY)

            if algo in ("orb", "feature_orb"):
                nfeatures = int(params.get("nfeatures", 2000))
                scaleFactor = float(params.get("scaleFactor", 1.2))
                nlevels = int(params.get("nlevels", 8))
                detector = cv2.ORB_create(nfeatures=nfeatures, scaleFactor=scaleFactor, nlevels=nlevels)
                norm = cv2.NORM_HAMMING
                matcher = cv2.BFMatcher(norm)
                knn_ok = True
            elif algo == "sift":
                try:
                    nfeatures = int(params.get("nfeatures", 0))
                    contrastThreshold = float(params.get("contrastThreshold", 0.04))
                    edgeThreshold = float(params.get("edgeThreshold", 10))
                    detector = cv2.SIFT_create(nfeatures=nfeatures, contrastThreshold=contrastThreshold, edgeThreshold=edgeThreshold)
                except Exception:
                    detector = cv2.SIFT_create()
                index_params = dict(algorithm=1, trees=5)
                search_params = dict(checks=50)
                matcher = cv2.FlannBasedMatcher(index_params, search_params)
                knn_ok = True
            elif algo == "akaze":
                detector = cv2.AKAZE_create()
                norm = cv2.NORM_HAMMING
                matcher = cv2.BFMatcher(norm)
                knn_ok = True
            else:
                logger.warning(f"unknown feature algo: {self.algo_type}; NG")
                return {"status": "NG", "ng_regions": []}

            kp1, des1 = detector.detectAndCompute(gray_tpl, None)
            kp2, des2 = detector.detectAndCompute(gray_crop, None)
            if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
                logger.info("feature descriptors insufficient; NG")
                return {"status": "NG", "ng_regions": []}

            if knn_ok:
                matches = matcher.knnMatch(des1, des2, k=2)
                good = []
                for m, n in matches:
                    if m.distance < 0.75 * n.distance:
                        good.append(m)
            else:
                matches = matcher.match(des1, des2)
                matches = sorted(matches, key=lambda m: m.distance)
                good = matches[:max(10, int(len(matches) * 0.2))]

            ratio = len(good) / float(max(1, len(kp1)))
            thr = float(step.get("tolerance", {}).get("min_match_score", params.get("min_match_score", 0.3)))
            logger.info(f"{algo} good={len(good)} ratio={ratio:.3f} threshold={thr:.3f} roi={roi}")

            if len(good) >= 4:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                if mask is not None:
                    inliers = int(mask.sum())
                    inlier_ratio = inliers / float(max(1, len(good)))
                    logger.info(f"{algo} homography inliers={inliers}/{len(good)} inlier_ratio={inlier_ratio:.3f}")
                    ratio = max(ratio, inlier_ratio)

            if ratio >= thr:
                return {"status": "OK", "ng_regions": []}
            if isinstance(roi, (list, tuple)) and len(roi) == 4:
                rx, ry, rw, rh = [int(v) for v in roi]
                return {"status": "NG", "ng_regions": [{"box_coords": [rx, ry, rx+rw, ry+rh]}]}
            return {"status": "NG", "ng_regions": []}
        except Exception:
            logger.exception("feature_match error")
            return {"status": "NG", "ng_regions": []}


class Engine:
    def __init__(self, process: Dict[str, Any]):
        self.process = process
        self.algorithms: Dict[str, Algorithm] = {}
        self._init_algorithms()
        self._global_bbox: Optional[Tuple[int, int, int, int]] = None

    def _init_algorithms(self) -> None:
        algo_defs = self.process.get("algorithms") or {}
        if isinstance(algo_defs, list):
            algo_dict = {}
            for a in algo_defs:
                algo_id = str(a.get("id", a.get("name", "default")))
                algo_type = str(a.get("type", "always_pass"))
                params = a.get("params", {})
                algo_dict[algo_id] = self._build_algo(algo_type, params)
            self.algorithms = algo_dict
        elif isinstance(algo_defs, dict):
            algo_dict = {}
            for algo_id, a in algo_defs.items():
                algo_type = str(a.get("type", "always_pass"))
                params = a.get("params", {})
                algo_dict[str(algo_id)] = self._build_algo(algo_type, params)
            self.algorithms = algo_dict
        else:
            self.algorithms = {"default": Algorithm("always_pass", {})}

    def _build_algo(self, algo_type: str, params: Dict[str, Any]) -> Algorithm:
        if str(algo_type).lower() in ("template_match", "tm", "template"):
            return TemplateMatchAlgorithm(algo_type, params)
        if str(algo_type).lower() in ("orb", "feature_orb", "sift", "akaze"):
            return KeypointFeatureAlgorithm(algo_type, params)
        return Algorithm(algo_type, params)

    def execute_step(self, image: Any, step_number: int) -> Dict[str, Any]:
        logger = logging.getLogger(__name__)
        steps = self.process.get("steps_detail") or self.process.get("steps") or []
        step = None
        if isinstance(steps, list):
            for s in steps:
                sn = s.get("step_number") or s.get("number")
                if int(sn or 0) == int(step_number):
                    step = s
                    break
        if step is None and isinstance(steps, list) and steps:
            step = steps[min(max(0, step_number - 1), len(steps) - 1)]
        algo_id = None
        if isinstance(step, dict):
            algo_id = step.get("algorithm_id") or step.get("algorithm")
        logger.info(f"execute_step number={step_number} algo_id={algo_id}")
        # ensure global bbox
        if self._global_bbox is None:
            self._global_bbox = _locate_global(image, self.process)
            if self._global_bbox is None:
                logger.error("global template not found; all steps fail")
                return {"status": "NG", "ng_regions": []}
            else:
                logger.info(f"using global bbox={self._global_bbox}")
        # inject roi as intersection with global bbox
        if self._global_bbox is not None:
            gx, gy, gw, gh = self._global_bbox
            roi = step.get("roi") or step.get("relative_roi")
            if isinstance(roi, (list, tuple)) and len(roi) == 4:
                rx, ry, rw, rh = [int(v) for v in roi]
                irx = max(gx, rx)
                iry = max(gy, ry)
                irw = max(1, min(gx + gw, rx + rw) - irx)
                irh = max(1, min(gy + gh, ry + rh) - iry)
                step = {**(step or {}), "roi": [irx, iry, irw, irh]}
            else:
                step = {**(step or {}), "roi": [gx, gy, gw, gh]}
        algo = self.algorithms.get(str(algo_id)) if algo_id is not None else None
        if algo is None:
            algo = self.algorithms.get("default") or Algorithm("always_pass", {})
        return algo.run(image, step or {})


def load_produce(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [normalize_process(p) for p in data]
    if isinstance(data, dict) and data.get("processes"):
        return [normalize_process(p) for p in data["processes"]]
    if isinstance(data, dict):
        return [normalize_process(data)]
    return []


def _decode_image_base64(img_b64: str) -> Optional[Any]:
    if np is None or cv2 is None:
        return None
    try:
        buf = base64.b64decode(img_b64)
        arr = np.frombuffer(buf, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def normalize_process(p: Dict[str, Any]) -> Dict[str, Any]:
    pf = p.get("process_file_info", {})
    name = pf.get("name") or p.get("name") or p.get("algorithm_name") or "工艺"
    version = pf.get("version") or p.get("version") or p.get("algorithm_version") or "v1.0.0"
    pid = p.get("pid") or p.get("id") or name
    summary = p.get("summary") or ""
    steps = p.get("steps_detail") or p.get("steps") or p.get("component_templates") or []
    preview_steps: List[Dict[str, Any]] = []
    if isinstance(steps, list):
        for s in steps[:8]:
            step_name = s.get("step_name") or s.get("name") or str(s.get("operation_guide", "步骤"))
            preview_steps.append({"step_name": str(step_name)})
    steps_detail: List[Dict[str, Any]] = []
    if isinstance(steps, list):
        for i, s in enumerate(steps):
            if "component_templates" in p:
                tpl_np = None
                img_b64 = s.get("image_base64")
                if isinstance(img_b64, str) and img_b64:
                    tpl_np = _decode_image_base64(img_b64)
                steps_detail.append({
                    "step_number": i + 1,
                    "step_name": s.get("step_name") or f"步骤 {i+1}",
                    "operation_guide": s.get("step_description") or s.get("qc_standard") or "",
                    "quality_standard": s.get("qc_standard") or "",
                    "algorithm_id": (p.get("process_file_info", {}).get("feature_algorithm") or "orb"),
                    "template_image_np": tpl_np,
                    "image_base64": img_b64,
                    "roi": s.get("relative_roi") or s.get("roi"),
                    "tolerance": s.get("tolerance") or {},
                })
            else:
                steps_detail.append({
                    "step_number": s.get("step_number", i + 1),
                    "step_name": s.get("step_name") or s.get("name") or f"步骤 {i+1}",
                    "operation_guide": s.get("operation_guide") or "",
                    "quality_standard": s.get("quality_standard") or "",
                    "algorithm_id": s.get("algorithm_id") or s.get("algorithm") or "default",
                    "template_image": s.get("template_image"),
                })
    algo_defs = p.get("algorithms") or {}
    if "component_templates" in p:
        pf = p.get("process_file_info", {})
        feat_algo = str(pf.get("feature_algorithm", "orb")).lower()
        feat_params = pf.get("feature_parameters", {})
        tol = p.get("tolerance") or {}
        min_thr = tol.get("min_match_score")
        if isinstance(min_thr, (int, float)):
            feat_params.setdefault("min_match_score", float(min_thr))
        algo_defs = {feat_algo: {"type": feat_algo, "params": feat_params}}
    return {
        "algorithm_name": name,
        "algorithm_version": version,
        "summary": summary,
        "pid": str(pid),
        "name": name,
        "steps_detail": steps_detail or (steps if isinstance(steps, list) else []),
        "steps": preview_steps,
        "algorithms": algo_defs,
        "globals": {
            **(p.get("globals") or {}),
            "global_template": p.get("global_template") or {},
            "global_template_np": _decode_image_base64((p.get("global_template") or {}).get("image_base64", "")) if (p.get("global_template") or {}).get("image_base64") else None
        },
    }


def get_info_from_json(json_path: str) -> List[Dict[str, Any]]:
    return load_produce(Path(json_path))


def get_info_from_directory(dir_path: str) -> List[Dict[str, Any]]:
    root = Path(dir_path)
    if not root.exists():
        return []
    items: List[Dict[str, Any]] = []
    for p in sorted(root.glob("*.json")):
        try:
            loaded = load_produce(p)
            for it in loaded:
                it["json_file"] = p.name
                it["json_path"] = str(p)
            items.extend(loaded)
        except Exception:
            continue
    return items


def _locate_global(image: Any, process: Dict[str, Any]) -> Optional[Tuple[int, int, int, int]]:
    logger = logging.getLogger(__name__)
    if cv2 is None or np is None:
        return None
    tpl_np = None
    g = process.get("globals", {})
    gt = g.get("global_template", {})
    tpl_np = g.get("global_template_np")
    if tpl_np is None:
        img_b64 = gt.get("image_base64")
        if isinstance(img_b64, str) and img_b64:
            tpl_np = _decode_image_base64(img_b64)
    if tpl_np is None:
        return None
    src = image if isinstance(image, np.ndarray) else np.array(image)
    gray_crop = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    gray_tpl = cv2.cvtColor(tpl_np, cv2.COLOR_BGR2GRAY)
    pf = process.get("process_file_info", {})
    algo = str(pf.get("feature_algorithm", "orb")).lower()
    params = pf.get("feature_parameters", {})
    if algo in ("orb", "feature_orb"):
        nfeatures = int(params.get("nfeatures", 2000))
        scaleFactor = float(params.get("scaleFactor", 1.2))
        nlevels = int(params.get("nlevels", 8))
        detector = cv2.ORB_create(nfeatures=nfeatures, scaleFactor=scaleFactor, nlevels=nlevels)
        norm = cv2.NORM_HAMMING
        matcher = cv2.BFMatcher(norm)
        knn_ok = True
    elif algo == "sift":
        try:
            nfeatures = int(params.get("nfeatures", 0))
            contrastThreshold = float(params.get("contrastThreshold", 0.04))
            edgeThreshold = float(params.get("edgeThreshold", 10))
            detector = cv2.SIFT_create(nfeatures=nfeatures, contrastThreshold=contrastThreshold, edgeThreshold=edgeThreshold)
        except Exception:
            detector = cv2.SIFT_create()
        index_params = dict(algorithm=1, trees=5)
        search_params = dict(checks=50)
        matcher = cv2.FlannBasedMatcher(index_params, search_params)
        knn_ok = True
    elif algo == "akaze":
        detector = cv2.AKAZE_create()
        norm = cv2.NORM_HAMMING
        matcher = cv2.BFMatcher(norm)
        knn_ok = True
    else:
        detector = cv2.ORB_create(nfeatures=2000, scaleFactor=1.2, nlevels=8)
        norm = cv2.NORM_HAMMING
        matcher = cv2.BFMatcher(norm)
        knn_ok = True
    kp1, des1 = detector.detectAndCompute(gray_tpl, None)
    kp2, des2 = detector.detectAndCompute(gray_crop, None)
    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        logger.info("global locate descriptors insufficient")
        return None
    if knn_ok:
        matches = matcher.knnMatch(des1, des2, k=2)
        good = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good.append(m)
    else:
        matches = matcher.match(des1, des2)
        matches = sorted(matches, key=lambda m: m.distance)
        good = matches[:max(10, int(len(matches) * 0.2))]
    logger.info(f"global locate algo={algo} good={len(good)}")
    if len(good) < 4:
        return None
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        return None
    h, w = gray_tpl.shape[:2]
    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    proj = cv2.perspectiveTransform(corners, H).reshape(-1, 2)
    xs = proj[:, 0]
    ys = proj[:, 1]
    x1 = max(0, int(xs.min()))
    y1 = max(0, int(ys.min()))
    x2 = min(src.shape[1], int(xs.max()))
    y2 = min(src.shape[0], int(ys.max()))
    if x2 <= x1 or y2 <= y1:
        return None
    logger.info(f"global bbox=({x1},{y1},{x2-x1},{y2-y1})")
    return (x1, y1, x2 - x1, y2 - y1)


def execute_step(image: Any, step_number: int, process: Dict[str, Any]) -> Dict[str, Any]:
    return Engine(process).execute_step(image, step_number)