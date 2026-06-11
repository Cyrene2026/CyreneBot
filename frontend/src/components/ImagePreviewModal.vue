<script setup lang="ts">
import { useFeed } from '../composables/useFeed'
import { imageSrc } from '../utils/format'

const { previewImage, imageForm } = useFeed()
</script>

<template>
  <section v-if="previewImage" class="modal-backdrop" @click.self="previewImage = null">
    <div class="image-preview-modal-content">
      <img :src="imageSrc(previewImage)" alt="预览" />
      <div class="image-preview-details">
        <h2>修订后的提示词</h2>
        <p>{{ previewImage.revised_prompt || imageForm.prompt }}</p>
        <div class="image-preview-actions">
          <a
            :href="imageSrc(previewImage)"
            :download="`generated_image_${Date.now()}.png`"
            class="primary-button"
          >
            下载
          </a>
          <button class="tool-button" type="button" @click="previewImage = null">关闭</button>
        </div>
      </div>
    </div>
  </section>
</template>
