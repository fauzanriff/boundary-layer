# -*- coding: utf-8 -*-
# Copyright 2018 Etsy Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

import marshmallow as ma
from boundary_layer.schemas.base import StrictSchema


class ResourceSpecSchema(StrictSchema):
    name = ma.fields.String(required=True)
    create_operator_type = ma.fields.String(required=True)
    destroy_operator_type = ma.fields.String()
    provides_args = ma.fields.List(ma.fields.String(), required=True)
    disable_sentinel_node = ma.fields.Boolean()
