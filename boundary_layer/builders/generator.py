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

from boundary_layer.builders.base import DagBuilderBase


class GeneratorBuilder(DagBuilderBase):
    indent_operators = True

    def preamble(self):
        assert len(self.reference_path) > 1, \
            'Invalid Generator reference path: {}'.format(self.reference_path)

        template = self.get_jinja_template('generator_preamble.j2')

        dag_args = {
            'dag_id': self.build_dag_id()
        }

        return template.render(
            generator_operator_name=self.dag['name'],
            dag_args=dag_args,
            specs=self.specs,
            referring_node=self.referring_node
        )

    def epilogue(self):
        template = self.get_jinja_template('generator_epilogue.j2')

        return template.render(
            upstream_surface=self.graph.get_upstream_surface(),
            downstream_surface=self.graph.get_downstream_surface())
