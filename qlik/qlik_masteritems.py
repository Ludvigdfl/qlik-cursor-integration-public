from qlik_sdk import AuthType, Config, Qlik
import json
import os
import sys
import requests
from pathlib import Path

class Qlik_Masteritems:

    @staticmethod
    def _load_config() -> dict:
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".qlik_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                return json.load(f)
        return {}

    def __init__(self, app_id: str, save_dir: Path = None):
        config = self._load_config()
        tenant_url = config.get("_QLIK_TENANT_URL_")
        self.api_key = config.get("_QLIK_API_KEY_")

        if not tenant_url:
            print("ERROR: _QLIK_TENANT_URL_ is not set. Run: qlik set_tenant <url>")
            sys.exit(1)
        if not self.api_key:
            print("ERROR: _QLIK_API_KEY_ is not set. Run: qlik set_tenant_api_key <key>")
            sys.exit(1)

        self.tenant_host = tenant_url.rstrip("/")
        self.app_id = app_id
        self.save_dir = save_dir or Path(__file__).parent
        self.app = None
        self.connect()

    def connect(self) -> None:
        config = Config(
            host=self.tenant_host,
            auth_type=AuthType.APIKey,
            api_key=self.api_key,
        )
        qlik = Qlik(config)
        self.app = qlik.apps.get(self.app_id)
        self.app.open()
 

    def close(self) -> None:
        if self.app:
            self.app.close()

    def master_measure_exists(self, title: str, id: str = None) -> list[dict]:
        """Returns a list of matching master measures as dicts. Empty list if none found, multiple entries if duplicates exist."""

        measures = self.app.create_session_object({
            "qInfo": {"qType": "MeasureList"},
            "qMeasureListDef": {
                "qType": "measure",
                "qData": {
                    "title": "/qMetaDef/title",
                    "qMeasure": "/qMeasure",
                    "description": "/qMetaDef/description",
                    "tags": "/qMetaDef/tags",
                }
            }
        })

        layout = measures.get_layout()
        return [
            {
                "id":          m.qInfo.qId,
                "title":       m.qMeta.title,
                "description": m.qMeta.description,
                "definition":  m.qData.qMeasure.get("qDef", ""),
                "label":       m.qData.qMeasure.get("qLabelExpression", ""),
                "fmt":         m.qData.qMeasure.get("qNumFormat", {}).get("qFmt", ""),
                "tags":        getattr(m.qData, "tags", []),
            }
            for m in layout.qMeasureList.qItems
            if (id is not None and m.qInfo.qId == id) or (id is None and m.qMeta.title == title)
        ]

    def delete_master_measure(self, title: str) -> bool:
        """Deletes a master measure by name. Returns True if deleted, False if not found."""

        measures = self.app.create_session_object({
            "qInfo": {"qType": "MeasureList"},
            "qMeasureListDef": {
                "qType": "measure",
                "qData": {
                    "title": "/qMetaDef/title",
                }
            }
        })

        layout = measures.get_layout()
        for m in layout.qMeasureList.qItems:
            if m.qMeta.title == title:
                print(f"Deleting master measure {title}")
                self.app.destroy_measure(m.qInfo.qId)
                self.app.do_save()
                return True
        return False

    def update_master_measure_expr(self, title: str, definition: str, description: str = "", label: str = "", tags: list = [], fmt: str = None, id: str = None) -> bool:
        """Updates an existing master measure in-place. Returns True if found and updated, False otherwise.
        If id is provided, matches by ID; otherwise matches by name."""

        measures = self.app.create_session_object({
            "qInfo": {"qType": "MeasureList"},
            "qMeasureListDef": {
                "qType": "measure",
                "qData": {"title": "/qMetaDef/title"}
            }
        })

        layout = measures.get_layout()
        for m in layout.qMeasureList.qItems:
            if id is not None and m.qInfo.qId == id or id is None and m.qMeta.title == title:
                measure_obj = self.app.get_measure(m.qInfo.qId)
                props = measure_obj.get_properties()
                num_format = {"qType": "F", "qFmt": fmt, "qDec": ".", "qThou": " ", "qUseThou": 1} if fmt else {"qType": "U"}
                props.qMeasure.qDef = definition
                props.qMeasure.qLabel = title
                props.qMeasure.qLabelExpression = label or title
                props.qMeasure.qNumFormat = num_format
                props.qMetaDef.title = title
                props.qMetaDef.description = description
                props.qMetaDef.tags = tags
                measure_obj.set_properties(props)
                self.app.do_save()
                return True
        return False

    def create_master_measure_expr(self, title: str, definition: str, description: str = "", label: str = "", tags: list = [], fmt: str = None, id: str = None) -> None:
        """Creates a master measure expression and saves it to the app."""

        num_format = {"qType": "F", "qFmt": fmt, "qDec": ".", "qThou": " ", "qUseThou": 1} if fmt else {"qType": "U"}

        self.app.create_measure({
            "qInfo": {
                "qType": "measure"
            },
            "qMeasure": {
                "qDef": definition,
                "qLabel": title,
                "qLabelExpression": label,
                "qNumFormat": num_format,
            },
            "qMetaDef": {
                "title": title,
                "description": description,
                "tags": tags,
            }
        })

        self.app.do_save()


    def create_measures(self, measures: list) -> None:
        """Creates or updates the given measures in the app. Raises on duplicates."""

        for measure in measures:
            args = dict(
                title=measure["title"],
                definition=measure["definition"],
                description=measure.get("description", ""),
                label=measure.get("label", ""),
                tags=measure.get("tags", []),
                fmt=measure.get("fmt"),
                id=measure.get("id", None),
            )

            matches = self.master_measure_exists(measure["title"], measure.get("id"))

            if len(matches) == 0:
                print(f"Creating: '{measure['title']}' ✅")
                self.create_master_measure_expr(**args)
            elif len(matches) == 1:
                print(f"Updating: '{measure['title']}' ✅")
                self.update_master_measure_expr(**args)
            else:
                ids = ", ".join(m["id"] for m in matches)
                raise ValueError(f"Duplicate measures found for title '{measure['title']}' (IDs: {ids}) — please resolve in measures.json and try again.")

    def master_dimension_exists(self, title: str, id: str = None) -> list[dict]:
        """Returns a list of matching master dimensions as dicts. Empty list if none found, multiple entries if duplicates exist."""

        dimensions = self.app.create_session_object({
            "qInfo": {"qType": "DimensionList"},
            "qDimensionListDef": {
                "qType": "dimension",
                "qData": {
                    "title": "/qMetaDef/title",
                    "qDim": "/qDim",
                    "description": "/qMetaDef/description",
                    "tags": "/qMetaDef/tags",
                }
            }
        })

        layout = dimensions.get_layout()
        return [
            {
                "id":          m.qInfo.qId,
                "title":       m.qMeta.title,
                "description": m.qMeta.description,
                "definition":        (m.qData.qDim.get("qFieldDefs") or [""])[0],
                "label":             (m.qData.qDim.get("qFieldLabels") or [""])[0],
                "label_expression":  m.qData.qDim.get("qLabelExpression", ""),
                "tags":              getattr(m.qData, "tags", []),
            }
            for m in layout.qDimensionList.qItems
            if (id is not None and m.qInfo.qId == id) or (id is None and m.qMeta.title == title)
        ]

    def delete_master_dimension(self, title: str) -> bool:
        """Deletes a master dimension by name. Returns True if deleted, False if not found."""

        dimensions = self.app.create_session_object({
            "qInfo": {"qType": "DimensionList"},
            "qDimensionListDef": {
                "qType": "dimension",
                "qData": {
                    "title": "/qMetaDef/title",
                }
            }
        })

        layout = dimensions.get_layout()
        for m in layout.qDimensionList.qItems:
            if m.qMeta.title == title:
                print(f"Deleting master dimension {title}")
                self.app.destroy_dimension(m.qInfo.qId)
                self.app.do_save()
                return True
        return False

    def update_master_dimension_expr(self, title: str, definition: str, description: str = "", label: str = "", tags: list = [], id: str = None, label_expression: str = "") -> bool:
        """Updates an existing master dimension in-place. Returns True if found and updated, False otherwise.
        If id is provided, matches by ID; otherwise matches by name."""

        dimensions = self.app.create_session_object({
            "qInfo": {"qType": "DimensionList"},
            "qDimensionListDef": {
                "qType": "dimension",
                "qData": {"title": "/qMetaDef/title"}
            }
        })

        layout = dimensions.get_layout()
        for m in layout.qDimensionList.qItems:
            if id is not None and m.qInfo.qId == id or id is None and m.qMeta.title == title:
                dimension_obj = self.app.get_dimension(m.qInfo.qId)
                props = dimension_obj.get_properties()
                props.qDim.qFieldDefs = [definition]
                props.qDim.qFieldLabels = [label or title]
                props.qDim.qLabelExpression = label_expression
                props.qMetaDef.title = title
                props.qMetaDef.description = description
                props.qMetaDef.tags = tags
                dimension_obj.set_properties(props)
                self.app.do_save()
                return True
        return False

    def create_master_dimension_expr(self, title: str, definition: str, description: str = "", label: str = "", tags: list = [], label_expression: str = "") -> None:
        """Creates a master dimension and saves it to the app."""

        self.app.create_dimension({
            "qInfo": {
                "qType": "dimension"
            },
            "qDim": {
                "qFieldDefs": [definition],
                "qFieldLabels": [label or title],
                "qLabelExpression": label_expression,
                "qGrouping": "N",
            },
            "qMetaDef": {
                "title": title,
                "description": description,
                "tags": tags,
            }
        })

        self.app.do_save()

    def create_dimensions(self, dimensions: list) -> None:
        """Creates or updates the given dimensions in the app. Raises on duplicates."""

        for dimension in dimensions:
            args = dict(
                title=dimension["title"],
                definition=dimension["definition"],
                description=dimension.get("description", ""),
                label=dimension.get("label", ""),
                tags=dimension.get("tags", []),
                id=dimension.get("id", None),
                label_expression=dimension.get("label_expression", ""),
            )

            matches = self.master_dimension_exists(dimension["title"], dimension.get("id"))

            if len(matches) == 0:
                print(f"Creating: '{dimension['title']}' ✅")
                create_args = {k: v for k, v in args.items() if k != "id"}
                self.create_master_dimension_expr(**create_args)
            elif len(matches) == 1:
                print(f"Updating: '{dimension['title']}' ✅")
                self.update_master_dimension_expr(**args)
            else:
                ids = ", ".join(m["id"] for m in matches)
                raise ValueError(f"Duplicate dimensions found for title '{dimension['title']}' (IDs: {ids}) — please resolve in dimensions.json and try again.")

    def get_measures(self) -> list[dict]:
        """Fetches all measures from the app and returns them as a sorted list."""

        measures = self.app.create_session_object({
            "qInfo": {"qType": "MeasureList"},
            "qMeasureListDef": {
                "qType": "measure",
                "qData": {
                    "title": "/qMetaDef/title",
                    "qMeasure": "/qMeasure",
                    "description": "/qMetaDef/description",
                    "tags": "/qMetaDef/tags",
                }
            }
        })

        layout = measures.get_layout()
        measures_list = [
            {
                "title":       m.qMeta.title,
                "id":          m.qInfo.qId,
                "description": m.qMeta.description,
                "definition":  m.qData.qMeasure.get("qDef", ""),
                "label":       m.qData.qMeasure.get("qLabelExpression", ""),
                "fmt":         m.qData.qMeasure.get("qNumFormat", {}).get("qFmt", ""),
                "tags":        getattr(m.qData, "tags", []),
            }
            for m in layout.qMeasureList.qItems
        ]
        measures_list.sort(key=lambda x: x["title"])
        return measures_list


    def publish_app(self) -> None:
        """Publish the shared space app to its managed space counterpart."""
        base_url = self.tenant_host.rstrip("/") + "/api/v1"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Resolve the item ID for the shared app
        url = f"{base_url}/items?resourceId={self.app_id}&resourceType=app"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        items = response.json().get("data", [])
        if not items:
            raise ValueError(f"No item found for app {self.app_id}")
        app_item_id = items[0]["id"]

        # Resolve the published (managed) app ID
        url = f"{base_url}/items/{app_item_id}/publisheditems"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        published = response.json().get("data", [])
        if not published or "resourceId" not in published[0]:
            raise ValueError(
                "Published app not found. If this app has never been published, publish it once from the UI first."
            )
        target_id = published[0]["resourceId"]

        # Publish shared → managed
        url = f"{base_url}/apps/{self.app_id}/publish"
        response = requests.put(url, headers=headers, json={"targetId": target_id})
        response.raise_for_status()
        name = response.json().get("attributes", {}).get("name", self.app_id)
        print(f"✅ '{name}' published successfully")

    def get_dimensions(self) -> list[dict]:
        """Fetches all master dimensions from the app and returns them as a sorted list."""

        dimensions = self.app.create_session_object({
            "qInfo": {"qType": "DimensionList"},
            "qDimensionListDef": {
                "qType": "dimension",
                "qData": {
                    "title": "/qMetaDef/title",
                    "qDim": "/qDim",
                    "description": "/qMetaDef/description",
                    "tags": "/qMetaDef/tags",
                }
            }
        })

        layout = dimensions.get_layout()
        dimensions_list = [
            {
                "title":            m.qMeta.title,
                "id":               m.qInfo.qId,
                "description":      m.qMeta.description,
                "definition":       (m.qData.qDim.get("qFieldDefs") or [""])[0],
                "label":            (m.qData.qDim.get("qFieldLabels") or [""])[0],
                "label_expression": m.qData.qDim.get("qLabelExpression", ""),
                "tags":             getattr(m.qData, "tags", []),
            }
            for m in layout.qDimensionList.qItems
        ]
        dimensions_list.sort(key=lambda x: x["title"])
        return dimensions_list

    
    def get_object_items(self) -> list[dict]:
        """Returns all chart objects across all sheets with their measures and dimensions.

        Each entry contains the object ID, type, sheet title, and lists of dimensions/measures.
        Each dimension/measure indicates whether it's a master item: qLibraryId (master) or inline (inline).
        """

        results = []

        for sheet_info in self._get_sheets():
            sheet_id    = sheet_info.qInfo.qId
            sheet_title = getattr(sheet_info.qData, "title", sheet_id)

            sheet_obj    = self.app.get_object(sheet_id)
            sheet_layout = sheet_obj.get_layout()
            children     = sheet_layout.qChildList.qItems if sheet_layout.qChildList else []

            for child in children:
                obj_id   = child.qInfo.qId
                obj_type = child.qInfo.qType

                obj   = self.app.get_object(obj_id)
                props = obj.get_properties()

                def _parse_hc(hc):
                    dims, meas = [], []
                    for dim in getattr(hc, "qDimensions", []):
                        library_id = getattr(dim, "qLibraryId", None) or None
                        if library_id:
                            dims.append({"type": "master", "library_id": library_id})
                        else:
                            field_defs = getattr(dim.qDef, "qFieldDefs", [])
                            dims.append({"type": "inline", "expression": field_defs[0] if field_defs else ""})
                    for mea in getattr(hc, "qMeasures", []):
                        library_id = getattr(mea, "qLibraryId", None) or None
                        if library_id:
                            meas.append({"type": "master", "library_id": library_id})
                        else:
                            expr = getattr(mea.qDef, "qDef", "")
                            meas.append({"type": "inline", "expression": expr})
                    return dims, meas

                hc = getattr(props, "qHyperCubeDef", None)
                if hc is not None:
                    dimensions, measures = _parse_hc(hc)
                else:
                    # Map objects: qUndoExclude is a plain dict with gaLayers,
                    # each layer is also a dict containing its own qHyperCubeDef dict
                    dimensions, measures = [], []
                    undo = getattr(props, "qUndoExclude", None) or {}
                    for layer in (undo.get("gaLayers", []) if isinstance(undo, dict) else []):
                        layer_hc = layer.get("qHyperCubeDef") if isinstance(layer, dict) else None
                        if layer_hc is None:
                            continue
                        for dim in layer_hc.get("qDimensions", []):
                            library_id = dim.get("qLibraryId") or None
                            if library_id:
                                dimensions.append({"type": "master", "library_id": library_id})
                            else:
                                field_defs = dim.get("qDef", {}).get("qFieldDefs", [])
                                dimensions.append({"type": "inline", "expression": field_defs[0] if field_defs else ""})
                        for mea in layer_hc.get("qMeasures", []):
                            library_id = mea.get("qLibraryId") or None
                            if library_id:
                                measures.append({"type": "master", "library_id": library_id})
                            else:
                                measures.append({"type": "inline", "expression": mea.get("qDef", {}).get("qDef", "")})
                    if not dimensions and not measures:
                        continue

                ext_props = getattr(props, "props", None)
                results.append({
                    "id":          obj_id,
                    "type":        obj_type,
                    "sheet_id":    sheet_id,
                    "sheet":       sheet_title,
                    "dimensions":  dimensions,
                    "measures":    measures,
                    "components":  getattr(props, "components", []),
                    "table_bg":    ext_props.get("tableBackgroundColor") if isinstance(ext_props, dict) else None,
                })
        return results

    def set_object_background(self, color: str) -> list[str]:
        """Highlights all objects with inline measures/dimensions by setting a background color.
        Saves the original components for each object to items_diff/diff.json before overwriting.

        Args:
            color: A hex color string, e.g. '#ffcccc'.

        Returns:
            List of object IDs that were updated.
        """

        items = self.get_object_items()

        def has_inline(item: dict) -> bool:
            return any(x["type"] == "inline" for x in item["dimensions"] + item["measures"])

        inline_items = [item for item in items if has_inline(item)]

        # Identify published sheets among those containing inline objects (cache objects to avoid redundant calls)
        published_sheet_objs = []
        published_sheet_ids  = []
        for sheet_id in {item["sheet_id"] for item in inline_items}:
            sheet_obj = self.app.get_object(sheet_id)
            if self._is_published(sheet_obj.get_layout()):
                published_sheet_objs.append(sheet_obj)
                published_sheet_ids.append(sheet_id)

        self._unpublish_sheets(published_sheet_objs)

        # Save originals so revert_inline_object_background can restore them
        originals = {
            item["id"]: {
                "type":       item["type"],
                "sheet":      item["sheet"],
                "components": item["components"],
                "table_bg":   item["table_bg"],
            }
            for item in inline_items
        }
        diff_path = self._items_diff_path
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        if diff_path.exists():
            print("Layout/Sheets/items_diff/diff.json already exists — skipping save to preserve originals. Run revert_chart_diffs first.")
        else:
            with open(diff_path, "w", encoding="utf-8") as f:
                json.dump({"originals": originals, "published_sheet_ids": published_sheet_ids}, f, indent=4)

        updated = []
        for item in inline_items:
            obj   = self.app.get_object(item["id"])
            props = obj.get_properties()
            props.components = [
                {
                    "key": "general",
                    "background": {
                        "mode": "color",
                        "color": {"color": color, "index": -1}
                    },
                    "bgColor": {
                        "color": {"index": -1, "color": color, "alpha": 1}
                    }
                }
            ]
            ext_props = getattr(props, "props", None)
            if isinstance(ext_props, dict) and "tableBackgroundColor" in ext_props:
                ext_props["tableBackgroundColor"] = color
            obj.set_properties(props)
            updated.append(item)

        self.app.do_save()
        self._publish_sheets(published_sheet_objs)

        current_sheet = None
        for item in updated:
            if item["sheet"] != current_sheet:
                if current_sheet is not None:
                    print()
                print(item["sheet"])
                current_sheet = item["sheet"]
            print(f" Flag object: [{item['type']}] {item['id']}")

        print(f"\nFound and flagged {len(updated)} object(s) using hard coded measures or dimensions")
        return updated

    def revert_object_background(self) -> list[str]:
        """Restores the original background components for all objects saved by set_inline_object_background.

        Returns:
            List of object IDs that were reverted.
        """

        diffs_path = self._items_diff_path
        if not diffs_path.exists():
            print("No Layout/Sheets/items_diff/diff.json found — nothing to revert.")
            return []

        with open(diffs_path, "r", encoding="utf-8") as f:
            saved = json.load(f)

        originals = saved["originals"] if "originals" in saved else saved
        original_obj_ids = set(originals.keys())

        # Check current sheet state at unflag-time (not what was saved at flag-time).
        # The user may have toggled sheets public/private between the two operations.
        sheets_to_unpublish = []
        existing_ids = set()
        for sheet_info in self._get_sheets():
            sheet_id  = sheet_info.qInfo.qId
            sheet_obj = self.app.get_object(sheet_id)
            layout    = sheet_obj.get_layout()
            child_ids = {child.qInfo.qId for child in (layout.qChildList.qItems or [])}
            existing_ids |= child_ids
            if self._is_published(layout) and (child_ids & original_obj_ids):
                sheets_to_unpublish.append(sheet_obj)

        self._unpublish_sheets(sheets_to_unpublish)

        reverted_items = []
        for obj_id, meta in originals.items():
            if obj_id not in existing_ids:
                print(f"  Skipped (deleted): {obj_id} on '{meta['sheet']}'")
                continue
            obj   = self.app.get_object(obj_id)
            props = obj.get_properties()
            props.components = meta["components"]
            if meta.get("table_bg") is not None:
                ext_props = getattr(props, "props", None)
                if isinstance(ext_props, dict) and "tableBackgroundColor" in ext_props:
                    ext_props["tableBackgroundColor"] = meta["table_bg"]
            obj.set_properties(props)
            reverted_items.append((obj_id, meta))

        self.app.do_save()
        diffs_path.unlink()
        diffs_path.parent.rmdir()

        reverted_items.sort(key=lambda x: x[1]["sheet"])
        current_sheet = None
        for obj_id, meta in reverted_items:
            if meta["sheet"] != current_sheet:
                if current_sheet is not None:
                    print()
                print(meta["sheet"])
                current_sheet = meta["sheet"]
            print(f" Unflag object: [{meta['type']}] {obj_id}")

        print(f"\nUnflagged {len(reverted_items)} object(s) using hard coded measures or dimensions")
        self._publish_sheets(sheets_to_unpublish)
        return [obj_id for obj_id, _ in reverted_items]

    def _check_duplicate_ids(self, items: list[dict], file_name: str) -> None:
        """Raises ValueError if any items share the same non-null ID."""
        ids = [item["id"] for item in items if item.get("id")]
        seen, duplicates = set(), set()
        for id_ in ids:
            if id_ in seen:
                duplicates.add(id_)
            seen.add(id_)
        if duplicates:
            self.close()
            raise ValueError(f"""Duplicate IDs found in {file_name}: {', '.join(sorted(duplicates))}
Each item must have a unique ID when publishing to qlik.
Correct and run set_items again."""
            )

    @property
    def _items_diff_path(self) -> Path:
        return self.save_dir.parent / "Layout" / "Sheets" / "items_diff" / "diff.json"

    @staticmethod
    def _is_published(layout) -> bool:
        return getattr(getattr(layout, "qMeta", None), "published", False)

    def _get_sheets(self):
        """Returns all sheet items from the app's SheetList."""
        sheet_list = self.app.create_session_object({
            "qInfo": {"qType": "SheetList"},
            "qAppObjectListDef": {
                "qType": "sheet",
                "qData": {"title": "/qMetaDef/title"}
            }
        })
        return sheet_list.get_layout().qAppObjectList.qItems

    def _unpublish_sheets(self, sheet_objs: list) -> None:
        """Temporarily unpublish a list of sheet objects to allow editing."""
        if not sheet_objs:
            return
        print(f"Temporarily unpublishing {len(sheet_objs)} published sheet(s) to allow editing...")
        for obj in sheet_objs:
            obj.un_publish()

    def _publish_sheets(self, sheet_objs: list) -> None:
        """Re-publish a list of sheet objects."""
        if not sheet_objs:
            return
        print(f"Re-publishing {len(sheet_objs)} sheet(s)...")
        for obj in sheet_objs:
            obj.publish()

    @staticmethod
    def _sdk_to_dict(obj):
        """Recursively convert an SDK model object to a plain dict/list."""
        if isinstance(obj, dict):
            return {k: Qlik_Masteritems._sdk_to_dict(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [Qlik_Masteritems._sdk_to_dict(i) for i in obj]
        if hasattr(obj, "__dict__"):
            return {k: Qlik_Masteritems._sdk_to_dict(v) for k, v in vars(obj).items() if not k.startswith("_")}
        return obj

    def get_objects(self, objects_root: Path) -> int:
        """Fetch all sheet objects and save each as a JSON file.

        Files are written to:
            objects_root / <sanitized_sheet_title> / <obj_id>.json

        The caller (CLI) is responsible for constructing objects_root as
            {project_root}/{space}/{app}/{appId}/Layout/Sheets

        Returns the total number of objects written.
        """

        total = 0

        for sheet_info in self._get_sheets():
            sheet_id    = sheet_info.qInfo.qId
            sheet_title = getattr(sheet_info.qData, "title", None) or sheet_id
            safe_title  = "".join(c if c.isalnum() or c in " _-" else "_" for c in sheet_title).strip()

            sheet_dir = objects_root / safe_title
            sheet_dir.mkdir(parents=True, exist_ok=True)

            sheet_obj    = self.app.get_object(sheet_id)
            sheet_layout = sheet_obj.get_layout()
            children     = sheet_layout.qChildList.qItems if sheet_layout.qChildList else []

            for child in children:
                obj_id = child.qInfo.qId
                obj    = self.app.get_object(obj_id)
                layout = obj.get_layout()
                data   = self._sdk_to_dict(layout)

                out_path = sheet_dir / f"{obj_id}.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                total += 1


        return total

    def _load_local_items(self) -> tuple[list[dict], list[dict]]:
        """Loads measures.json and dimensions.json from the save directory. Raises clearly if either file is missing."""
        measures_path = self.save_dir / "measures.json"
        dimensions_path = self.save_dir / "dimensions.json"

        if not measures_path.exists():
            raise FileNotFoundError(f"measures.json not found in {self.save_dir} — make sure the file is named exactly 'measures.json'.")
        if not dimensions_path.exists():
            raise FileNotFoundError(f"dimensions.json not found in {self.save_dir} — make sure the file is named exactly 'dimensions.json'.")

        with open(measures_path, "r", encoding="utf-8") as f:
            measures = json.load(f)
        with open(dimensions_path, "r", encoding="utf-8") as f:
            dimensions = json.load(f)

        return measures, dimensions

    def get_items_changed(self) -> tuple[list[dict], list[dict]]:
        """Returns only the measures and dimensions that differ between local JSON files and the current Qlik app state."""

        local_measures, local_dimensions = self._load_local_items()

        self._check_duplicate_ids(local_measures, "measures.json")
        self._check_duplicate_ids(local_dimensions, "dimensions.json")

        fetched_measures = self.get_measures()
        fetched_dimensions = self.get_dimensions()

        fetched_measures_by_id = {m["id"]: m for m in fetched_measures}
        fetched_dimensions_by_id = {d["id"]: d for d in fetched_dimensions}

        measure_fields = ["title", "description", "definition", "label", "fmt", "tags"]
        dimension_fields = ["title", "description", "definition", "label", "label_expression", "tags"]

        def is_measure_changed(local: dict) -> bool:
            fetched = fetched_measures_by_id.get(local.get("id"))
            if fetched is None:
                return True
            return any(local.get(f) != fetched.get(f) for f in measure_fields)

        def is_dimension_changed(local: dict) -> bool:
            fetched = fetched_dimensions_by_id.get(local.get("id"))
            if fetched is None:
                return True
            return any(local.get(f) != fetched.get(f) for f in dimension_fields)

        changed_measures = [m for m in local_measures if is_measure_changed(m)]
        changed_dimensions = [d for d in local_dimensions if is_dimension_changed(d)]

        print(f"Changes detected: {len(changed_measures)} measure(s), {len(changed_dimensions)} dimension(s)")
        return changed_measures, changed_dimensions