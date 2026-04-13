export type SubjectType = 'food' | 'product';

export type GenerateImageParams = {
  image?: File;
  refImage?: File;
  userPrompt?: string;
  mood: string;
  subjectType: SubjectType;
  size: string;
};

export type GenerateResult = {
  ad_copy: string;
  image_b64: string;
};

export type GenerateImageResponse = {
  product_description: string;
  hashtags: string[];
  results: GenerateResult[];
};

export async function generateImage(
  params: GenerateImageParams
): Promise<GenerateImageResponse> {
  const formData = new FormData();

  if (params.image) {
    formData.append('image', params.image);
  }
  if (params.refImage) {
    formData.append('ref_image', params.refImage);
  }
  if (params.userPrompt) {
    formData.append('user_prompt', params.userPrompt);
  }

  formData.append('mood', params.mood);
  formData.append('subject_type', params.subjectType);
  formData.append('size', params.size);

  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const detail = body?.detail ?? `Server error: ${response.status}`;
      throw new Error(detail);
    }

    const data: GenerateImageResponse = await response.json();
    return data;
  } catch (error) {
    if (error instanceof Error) {
      throw new Error(`이미지 생성에 실패했습니다: ${error.message}`);
    }
    throw new Error('이미지 생성에 실패했습니다. 다시 시도해주세요.');
  }
}
